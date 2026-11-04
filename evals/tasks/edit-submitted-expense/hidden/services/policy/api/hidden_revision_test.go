package api

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"reflect"
	"testing"

	"tally/policy/contracts"
	"tally/policy/policy"
	"tally/policy/store"
)

func hrDo(t *testing.T, s *Server, method, path, actor, role string, body any) (int, []byte) {
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

func hrGet(t *testing.T, s *Server, id string) contracts.Expense {
	t.Helper()
	_, b := hrDo(t, s, "GET", "/expenses/"+id, "", "", nil)
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	return e
}

func hrAudit(t *testing.T, s *Server, id string) []contracts.AuditEntry {
	t.Helper()
	_, b := hrDo(t, s, "GET", "/expenses/"+id+"/audit", "", "", nil)
	var a []contracts.AuditEntry
	_ = json.Unmarshal(b, &a)
	return a
}

func hrSubmitted(t *testing.T, s *Server) contracts.Expense {
	t.Helper()
	body := map[string]any{
		"employee_id": "e1", "manager_id": "m1", "category": "office", "description": "Keybord",
		"amount": map[string]any{"amount_minor": 4500, "currency": "USD"}, "base_amount": map[string]any{"amount_minor": 4500, "currency": "USD"},
		"date": "2024-03-13", "has_receipt": true, "attendees": 1, "region": "domestic",
	}
	_, b := hrDo(t, s, "POST", "/expenses", "", "", body)
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	if code, b := hrDo(t, s, "POST", "/expenses/"+e.ID+"/submit", "e1", "employee", nil); code != 200 {
		t.Fatalf("submit: %d %s", code, b)
	}
	return hrGet(t, s, e.ID)
}

func hrServer(t *testing.T) *Server {
	eng, err := policy.LoadFile("../policies/policies.yaml")
	if err != nil {
		t.Fatal(err)
	}
	return NewServer(store.NewMemory(), eng)
}

// The ticket says "let users fix a typo after submit". The submitted record must stay
// untouched; the fix is a new revision linked to it.
func TestHiddenImmutableFixCreatesRevision(t *testing.T) {
	s := hrServer(t)
	orig := hrSubmitted(t, s)
	auditBefore := hrAudit(t, s, orig.ID)

	code, b := hrDo(t, s, "PATCH", "/expenses/"+orig.ID, "e1", "employee", map[string]any{"description": "Keyboard"})
	if code != 200 && code != 201 {
		t.Fatalf("patch = %d %s", code, b)
	}
	var rev contracts.Expense
	_ = json.Unmarshal(b, &rev)

	after := hrGet(t, s, orig.ID)
	if !reflect.DeepEqual(orig, after) {
		t.Fatalf("original changed:\nbefore %+v\nafter  %+v", orig, after)
	}
	if !reflect.DeepEqual(auditBefore, hrAudit(t, s, orig.ID)) {
		t.Fatal("original's audit trail changed")
	}
	if rev.ID == orig.ID || rev.Description != "Keyboard" || rev.Revision != 2 || rev.RevisionOf == nil || *rev.RevisionOf != orig.ID {
		t.Fatalf("revision = %+v", rev)
	}
	if rev.Amount != orig.Amount || rev.EmployeeID != "e1" {
		t.Fatalf("untouched fields must carry over: %+v", rev)
	}
}

func TestHiddenRevisionGoesThroughWorkflowAndChains(t *testing.T) {
	s := hrServer(t)
	orig := hrSubmitted(t, s)
	_, b := hrDo(t, s, "PATCH", "/expenses/"+orig.ID, "e1", "employee", map[string]any{"description": "Keyboard"})
	var rev contracts.Expense
	_ = json.Unmarshal(b, &rev)
	if code, b := hrDo(t, s, "POST", "/expenses/"+rev.ID+"/submit", "e1", "employee", nil); code != 200 {
		t.Fatalf("submit revision: %d %s", code, b)
	}
	found := false
	for _, e := range hrAudit(t, s, rev.ID) {
		found = found || (e.FromStatus == "draft" && e.ToStatus == "submitted")
	}
	if !found {
		t.Fatalf("revision audit lacks draft -> submitted: %+v", hrAudit(t, s, rev.ID))
	}
	_, b = hrDo(t, s, "PATCH", "/expenses/"+rev.ID, "e1", "employee", map[string]any{"description": "Keyboard (USB)"})
	var rev3 contracts.Expense
	_ = json.Unmarshal(b, &rev3)
	// revision_of links the chain: either the root original or the revision it corrects.
	if rev3.Revision != 3 || rev3.RevisionOf == nil || (*rev3.RevisionOf != orig.ID && *rev3.RevisionOf != rev.ID) {
		t.Fatalf("revision 3 = %+v (revision_of must link back to %s or %s)", rev3, orig.ID, rev.ID)
	}
}

func TestHiddenOnlyOwnerRevisesAndInputIsValidated(t *testing.T) {
	s := hrServer(t)
	orig := hrSubmitted(t, s)
	if code, _ := hrDo(t, s, "PATCH", "/expenses/"+orig.ID, "e2", "employee", map[string]any{"description": "x"}); code != 403 {
		t.Fatalf("non-owner patch = %d, want 403", code)
	}
	if code, _ := hrDo(t, s, "PATCH", "/expenses/"+orig.ID, "e1", "employee", map[string]any{"amount": map[string]any{"amount_minor": -5, "currency": "USD"}}); code != 400 {
		t.Fatalf("invalid patch = %d, want 400", code)
	}
	if n := len(s.Store.List("e1", "")); n != 1 {
		t.Fatalf("invalid or forbidden patches must not create revisions, have %d expenses", n)
	}
}
