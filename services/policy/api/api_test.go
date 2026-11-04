package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"tally/policy/contracts"
	"tally/policy/policy"
	"tally/policy/store"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	eng, err := policy.LoadFile("../policies/policies.yaml")
	if err != nil {
		t.Fatal(err)
	}
	s := NewServer(store.NewMemory(), eng)
	s.Now = func() time.Time { return time.Date(2024, 3, 15, 9, 0, 0, 0, time.UTC) }
	return s
}

func call(t *testing.T, s *Server, method, path, actorID, role string, body any) (int, []byte) {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		_ = json.NewEncoder(&buf).Encode(body)
	}
	req := httptest.NewRequest(method, path, &buf)
	if actorID != "" {
		req.Header.Set("X-Actor-ID", actorID)
		req.Header.Set("X-Actor-Role", role)
	}
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	return rec.Code, rec.Body.Bytes()
}

func expenseBody(emp, cat string, usd int64) map[string]any {
	return map[string]any{
		"employee_id": emp, "manager_id": "m9", "category": cat, "description": "test",
		"amount":      map[string]any{"amount_minor": usd, "currency": "USD"},
		"base_amount": map[string]any{"amount_minor": usd, "currency": "USD"},
		"date":        "2024-03-13", "has_receipt": true, "attendees": 1, "region": "domestic",
	}
}

func createAndSubmit(t *testing.T, s *Server, emp, cat string, usd int64) contracts.Expense {
	t.Helper()
	code, b := call(t, s, "POST", "/expenses", "", "", expenseBody(emp, cat, usd))
	if code != 201 {
		t.Fatalf("create: %d %s", code, b)
	}
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	code, b = call(t, s, "POST", "/expenses/"+e.ID+"/submit", emp, "employee", nil)
	if code != 200 {
		t.Fatalf("submit: %d %s", code, b)
	}
	var out struct{ Expense contracts.Expense }
	_ = json.Unmarshal(b, &out)
	return out.Expense
}

func audit(t *testing.T, s *Server, id string) []contracts.AuditEntry {
	t.Helper()
	_, b := call(t, s, "GET", "/expenses/"+id+"/audit", "", "", nil)
	var a []contracts.AuditEntry
	_ = json.Unmarshal(b, &a)
	return a
}

func TestLifecycleWritesAuditTrail(t *testing.T) {
	s := newTestServer(t)
	e := createAndSubmit(t, s, "e1", "lodging", 50000)
	if e.Status != contracts.ExpenseStatusPendingManager {
		t.Fatalf("status = %s", e.Status)
	}
	if code, b := call(t, s, "POST", "/expenses/"+e.ID+"/approve", "m1", "manager", map[string]string{"reason": "ok"}); code != 200 {
		t.Fatalf("approve: %d %s", code, b)
	}
	if code, b := call(t, s, "POST", "/expenses/"+e.ID+"/reimburse", "f1", "finance", nil); code != 200 {
		t.Fatalf("reimburse: %d %s", code, b)
	}
	a := audit(t, s, e.ID)
	want := [][2]string{{"draft", "submitted"}, {"submitted", "pending_manager"}, {"pending_manager", "approved"}, {"approved", "reimbursed"}}
	if len(a) != len(want) {
		t.Fatalf("audit has %d entries, want %d: %+v", len(a), len(want), a)
	}
	for i, w := range want {
		if a[i].FromStatus != w[0] || a[i].ToStatus != w[1] || a[i].At == "" || a[i].Actor == "" || a[i].Seq != int64(i+1) {
			t.Errorf("entry %d = %+v, want %v", i, a[i], w)
		}
	}
}

func TestAutoApprovedAndRejectedOutcomes(t *testing.T) {
	s := newTestServer(t)
	if e := createAndSubmit(t, s, "e1", "office", 1500); e.Status != contracts.ExpenseStatusAutoApproved {
		t.Fatalf("status = %s", e.Status)
	}
	body := expenseBody("e1", "travel", 5000)
	body["has_receipt"] = false
	_, b := call(t, s, "POST", "/expenses", "", "", body)
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	code, b := call(t, s, "POST", "/expenses/"+e.ID+"/submit", "e1", "employee", nil)
	if code != 200 || !bytes.Contains(b, []byte(`"rejected"`)) {
		t.Fatalf("expected rejected: %d %s", code, b)
	}
}

func TestOnlyOwnerSubmitsAndCannotResubmit(t *testing.T) {
	s := newTestServer(t)
	_, b := call(t, s, "POST", "/expenses", "", "", expenseBody("e1", "office", 1000))
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	if code, _ := call(t, s, "POST", "/expenses/"+e.ID+"/submit", "e2", "employee", nil); code != 403 {
		t.Fatalf("non-owner submit = %d, want 403", code)
	}
	call(t, s, "POST", "/expenses/"+e.ID+"/submit", "e1", "employee", nil)
	if code, _ := call(t, s, "POST", "/expenses/"+e.ID+"/submit", "e1", "employee", nil); code != 409 {
		t.Fatalf("resubmit = %d, want 409", code)
	}
}

func TestValidationRejectsFloatsAndBadBase(t *testing.T) {
	s := newTestServer(t)
	body := expenseBody("e1", "office", 1000)
	body["amount"] = map[string]any{"amount_minor": 10.5, "currency": "USD"}
	if code, _ := call(t, s, "POST", "/expenses", "", "", body); code != 400 {
		t.Fatalf("float amount = %d, want 400", code)
	}
	body = expenseBody("e1", "office", 1000)
	body["base_amount"] = map[string]any{"amount_minor": 1000, "currency": "EUR"}
	if code, _ := call(t, s, "POST", "/expenses", "", "", body); code != 400 {
		t.Fatalf("non-base currency = %d, want 400", code)
	}
}

func TestSameDayMealsAccumulate(t *testing.T) {
	s := newTestServer(t)
	if e := createAndSubmit(t, s, "e1", "meals", 5000); e.Status != contracts.ExpenseStatusAutoApproved {
		t.Fatalf("first meal = %s", e.Status)
	}
	if e := createAndSubmit(t, s, "e1", "meals", 3000); e.Status != contracts.ExpenseStatusPendingManager {
		t.Fatalf("second meal pushes over cap, got %s", e.Status)
	}
}

func TestReportAggregatesApprovedSpend(t *testing.T) {
	s := newTestServer(t)
	createAndSubmit(t, s, "e1", "office", 1500)
	createAndSubmit(t, s, "e1", "office", 2500)
	createAndSubmit(t, s, "e2", "lodging", 50000) // pending, not counted in totals
	_, b := call(t, s, "GET", "/reports", "", "", nil)
	var r contracts.Report
	if err := json.Unmarshal(b, &r); err != nil {
		t.Fatal(err)
	}
	if len(r.Rows) != 1 || r.Rows[0].Total.AmountMinor != 4000 || r.Rows[0].Count != 2 || r.Rows[0].Month != "2024-03" || r.Rows[0].Total.Currency != "USD" {
		t.Fatalf("rows = %+v", r.Rows)
	}
	counts := map[string]int64{}
	for _, c := range r.StatusCounts {
		counts[c.Status] = c.Count
	}
	if counts["auto_approved"] != 2 || counts["pending_manager"] != 1 {
		t.Fatalf("counts = %v", counts)
	}
}

func TestMissingActorHeaders(t *testing.T) {
	s := newTestServer(t)
	_, b := call(t, s, "POST", "/expenses", "", "", expenseBody("e1", "office", 1000))
	var e contracts.Expense
	_ = json.Unmarshal(b, &e)
	if code, _ := call(t, s, "POST", "/expenses/"+e.ID+"/submit", "", "", nil); code != 400 {
		t.Fatalf("no headers = %d, want 400", code)
	}
	if code, _ := call(t, s, "GET", "/expenses/nope", "", "", nil); code != http.StatusNotFound {
		t.Fatalf("missing = %d, want 404", code)
	}
}
