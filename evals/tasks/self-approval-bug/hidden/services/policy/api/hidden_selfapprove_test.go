package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"tally/policy/contracts"
	"tally/policy/policy"
	"tally/policy/store"
)

func hsDo(t *testing.T, s *Server, method, path, actor, role string, body any) (int, []byte) {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		_ = json.NewEncoder(&buf).Encode(body)
	}
	req := httptest.NewRequest(method, path, &buf)
	if actor != "" {
		req.Header.Set("X-Actor-ID", actor)
		req.Header.Set("X-Actor-Role", role)
	}
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	return rec.Code, rec.Body.Bytes()
}

func hsSubmitted(t *testing.T, s *Server, emp, role, cat string, usd int64) contracts.Expense {
	t.Helper()
	body := map[string]any{
		"employee_id": emp, "manager_id": "m9", "category": cat, "description": "x",
		"amount": map[string]any{"amount_minor": usd, "currency": "USD"}, "base_amount": map[string]any{"amount_minor": usd, "currency": "USD"},
		"date": "2024-03-13", "has_receipt": true, "attendees": 1, "region": "domestic",
	}
	_, b := hsDo(t, s, "POST", "/expenses", "", "", body)
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	if code, b := hsDo(t, s, "POST", "/expenses/"+e.ID+"/submit", emp, role, nil); code != 200 {
		t.Fatalf("submit: %d %s", code, b)
	}
	return e
}

func hsServer(t *testing.T) *Server {
	eng, err := policy.LoadFile("../policies/policies.yaml")
	if err != nil {
		t.Fatal(err)
	}
	return NewServer(store.NewMemory(), eng)
}

func hsAuditStatuses(t *testing.T, s *Server, id string) []string {
	_, b := hsDo(t, s, "GET", "/expenses/"+id+"/audit", "", "", nil)
	var a []contracts.AuditEntry
	_ = json.Unmarshal(b, &a)
	out := []string{}
	for _, e := range a {
		out = append(out, e.ToStatus)
	}
	return out
}

func TestHiddenManagerCannotApproveOwnExpense(t *testing.T) {
	s := hsServer(t)
	e := hsSubmitted(t, s, "m1", "manager", "lodging", 50000)
	if code, _ := hsDo(t, s, "POST", "/expenses/"+e.ID+"/approve", "m1", "manager", map[string]string{"reason": "me"}); code != http.StatusForbidden {
		t.Fatalf("self-approve = %d, want 403", code)
	}
	if code, _ := hsDo(t, s, "POST", "/expenses/"+e.ID+"/reject", "m1", "manager", nil); code != http.StatusForbidden {
		t.Fatalf("self-reject = %d, want 403", code)
	}
	_, b := hsDo(t, s, "GET", "/expenses/"+e.ID, "", "", nil)
	var got contracts.Expense
	_ = json.Unmarshal(b, &got)
	if got.Status != contracts.ExpenseStatusPendingManager {
		t.Fatalf("status = %s, want pending_manager", got.Status)
	}
	for _, st := range hsAuditStatuses(t, s, e.ID) {
		if st == "approved" || st == "rejected" {
			t.Fatalf("audit contains %s after a denied attempt", st)
		}
	}
}

func TestHiddenFinanceCannotApproveOwnExpense(t *testing.T) {
	s := hsServer(t)
	e := hsSubmitted(t, s, "f1", "finance", "lodging", 150000)
	if code, _ := hsDo(t, s, "POST", "/expenses/"+e.ID+"/approve", "f1", "finance", nil); code != http.StatusForbidden {
		t.Fatalf("finance self-approve = %d, want 403", code)
	}
}

func TestHiddenOtherManagerCanApproveAndIsAudited(t *testing.T) {
	s := hsServer(t)
	e := hsSubmitted(t, s, "m1", "manager", "lodging", 50000)
	if code, b := hsDo(t, s, "POST", "/expenses/"+e.ID+"/approve", "m2", "manager", map[string]string{"reason": "ok"}); code != 200 {
		t.Fatalf("approve by another manager = %d %s", code, b)
	}
	_, b := hsDo(t, s, "GET", "/expenses/"+e.ID+"/audit", "", "", nil)
	var a []contracts.AuditEntry
	_ = json.Unmarshal(b, &a)
	last := a[len(a)-1]
	if last.Actor != "m2" || last.ToStatus != "approved" || last.Reason != "ok" {
		t.Fatalf("last audit = %+v", last)
	}
}
