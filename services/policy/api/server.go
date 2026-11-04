// Package api exposes the policy service over HTTP. Handlers only translate
// HTTP to workflow/policy calls; they contain no policy logic.
package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"sort"
	"time"

	"tally/policy/contracts"
	"tally/policy/policy"
	"tally/policy/policy/rules"
	"tally/policy/store"
	"tally/policy/workflow"
)

const BaseCurrency = "USD"

type Server struct {
	Store  *store.Memory
	Engine *policy.Engine
	Now    func() time.Time
	mux    *http.ServeMux
}

func NewServer(s *store.Memory, e *policy.Engine) *Server {
	srv := &Server{Store: s, Engine: e, Now: time.Now, mux: http.NewServeMux()}
	srv.mux.HandleFunc("POST /expenses", srv.create)
	srv.mux.HandleFunc("GET /expenses", srv.list)
	srv.mux.HandleFunc("GET /expenses/{id}", srv.get)
	srv.mux.HandleFunc("POST /expenses/{id}/submit", srv.submit)
	srv.mux.HandleFunc("POST /expenses/{id}/approve", srv.decide(contracts.ExpenseStatusApproved))
	srv.mux.HandleFunc("POST /expenses/{id}/reject", srv.decide(contracts.ExpenseStatusRejected))
	srv.mux.HandleFunc("POST /expenses/{id}/reimburse", srv.decide(contracts.ExpenseStatusReimbursed))
	srv.mux.HandleFunc("GET /expenses/{id}/audit", srv.audit)
	srv.mux.HandleFunc("POST /policy/evaluate", srv.evaluate)
	srv.mux.HandleFunc("GET /policies", srv.policies)
	srv.mux.HandleFunc("GET /reports", srv.report)
	return srv
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) { s.mux.ServeHTTP(w, r) }

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, err error) {
	code := http.StatusInternalServerError
	switch {
	case errors.Is(err, store.ErrNotFound):
		code = http.StatusNotFound
	case errors.Is(err, workflow.ErrForbidden):
		code = http.StatusForbidden
	case errors.Is(err, workflow.ErrIllegalTransition):
		code = http.StatusConflict
	case errors.Is(err, errBadRequest):
		code = http.StatusBadRequest
	}
	writeJSON(w, code, map[string]string{"error": err.Error()})
}

var errBadRequest = errors.New("bad request")

func bad(format string, a ...any) error {
	return fmt.Errorf("%s: %w", fmt.Sprintf(format, a...), errBadRequest)
}

// actor reads the caller identity. Demo only: a real deployment would verify a token.
func actor(r *http.Request) (workflow.Actor, error) {
	id, role := r.Header.Get("X-Actor-ID"), r.Header.Get("X-Actor-Role")
	if id == "" || role == "" {
		return workflow.Actor{}, bad("X-Actor-ID and X-Actor-Role headers required")
	}
	switch contracts.ActorRole(role) {
	case contracts.ActorRoleEmployee, contracts.ActorRoleManager, contracts.ActorRoleFinance:
	default:
		return workflow.Actor{}, bad("unknown role %q", role)
	}
	return workflow.Actor{ID: id, Role: contracts.ActorRole(role)}, nil
}

func validate(e contracts.Expense) error {
	if e.EmployeeID == "" || e.ManagerID == "" {
		return bad("employee_id and manager_id required")
	}
	if e.Amount.Currency == "" || e.Amount.AmountMinor <= 0 {
		return bad("amount must be a positive integer in minor units with a currency")
	}
	if e.BaseAmount.Currency != BaseCurrency || e.BaseAmount.AmountMinor <= 0 {
		return bad("base_amount must be positive %s minor units", BaseCurrency)
	}
	if _, err := time.Parse("2006-01-02", e.Date); err != nil {
		return bad("date must be YYYY-MM-DD")
	}
	switch e.Category {
	case contracts.ExpenseCategoryMeals, contracts.ExpenseCategoryTravel, contracts.ExpenseCategoryLodging,
		contracts.ExpenseCategorySoftware, contracts.ExpenseCategoryAlcohol, contracts.ExpenseCategoryOffice, contracts.ExpenseCategoryOther:
	default:
		return bad("unknown category %q", e.Category)
	}
	return nil
}

func decodeExpense(r *http.Request) (contracts.Expense, error) {
	var e contracts.Expense
	if err := json.NewDecoder(r.Body).Decode(&e); err != nil {
		return e, bad("invalid JSON: %v", err)
	}
	if e.Attendees < 1 {
		e.Attendees = 1
	}
	if e.Region == "" {
		e.Region = contracts.RegionDomestic
	}
	if e.CreatedAt == "" {
		e.CreatedAt = time.Now().UTC().Format(time.RFC3339)
	}
	return e, validate(e)
}

func (s *Server) create(w http.ResponseWriter, r *http.Request) {
	e, err := decodeExpense(r)
	if err != nil {
		writeErr(w, err)
		return
	}
	e.RevisionOf = nil
	writeJSON(w, http.StatusCreated, s.Store.Create(e))
}

func (s *Server) list(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.Store.List(r.URL.Query().Get("employee_id"), r.URL.Query().Get("status")))
}

func (s *Server) get(w http.ResponseWriter, r *http.Request) {
	e, err := s.Store.Get(r.PathValue("id"))
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, e)
}

func (s *Server) context(e contracts.Expense) rules.Context {
	return rules.Context{PriorDayMinor: s.Store.PriorDaySpend(e.EmployeeID, string(e.Category), e.Date, e.ID)}
}

func (s *Server) submit(w http.ResponseWriter, r *http.Request) {
	a, err := actor(r)
	if err != nil {
		writeErr(w, err)
		return
	}
	id := r.PathValue("id")
	if _, err := s.Store.Transition(id, func(e *contracts.Expense) (contracts.AuditEntry, error) {
		return workflow.Apply(e, contracts.ExpenseStatusSubmitted, a, "submitted by owner", s.Now())
	}); err != nil {
		writeErr(w, err)
		return
	}
	e, _ := s.Store.Get(id)
	d := s.Engine.Evaluate(e, s.context(e))
	e, err = s.Store.Transition(id, func(e *contracts.Expense) (contracts.AuditEntry, error) {
		return workflow.Apply(e, contracts.ExpenseStatus(d.Outcome), workflow.System, d.Reason, s.Now())
	})
	if err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"expense": e, "decision": d})
}

func (s *Server) decide(to contracts.ExpenseStatus) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		a, err := actor(r)
		if err != nil {
			writeErr(w, err)
			return
		}
		var body struct {
			Reason string `json:"reason"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		e, err := s.Store.Transition(r.PathValue("id"), func(e *contracts.Expense) (contracts.AuditEntry, error) {
			return workflow.Apply(e, to, a, body.Reason, s.Now())
		})
		if err != nil {
			writeErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, e)
	}
}

func (s *Server) audit(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if _, err := s.Store.Get(id); err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, s.Store.Log.For(id))
}

// evaluate is a dry run: it never stores anything.
func (s *Server) evaluate(w http.ResponseWriter, r *http.Request) {
	e, err := decodeExpense(r)
	if err != nil {
		writeErr(w, err)
		return
	}
	e.ID = "preview"
	writeJSON(w, http.StatusOK, s.Engine.Evaluate(e, s.context(e)))
}

func (s *Server) policies(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, s.Engine.Rules())
}

// report aggregates approved spend (auto_approved, approved, reimbursed) in the
// base currency by employee, category and month, plus counts by status.
func (s *Server) report(w http.ResponseWriter, _ *http.Request) {
	type key struct{ emp, cat, month string }
	sums := map[key]*contracts.ReportRow{}
	counts := map[string]int64{}
	for _, e := range s.Store.List("", "") {
		counts[string(e.Status)]++
		switch e.Status {
		case contracts.ExpenseStatusAutoApproved, contracts.ExpenseStatusApproved, contracts.ExpenseStatusReimbursed:
		default:
			continue
		}
		k := key{e.EmployeeID, string(e.Category), e.Date[:7]}
		row := sums[k]
		if row == nil {
			row = &contracts.ReportRow{EmployeeID: k.emp, Category: k.cat, Month: k.month, Total: contracts.Money{Currency: BaseCurrency}}
			sums[k] = row
		}
		row.Total.AmountMinor += e.BaseAmount.AmountMinor
		row.Count++
	}
	rep := contracts.Report{Rows: []contracts.ReportRow{}, StatusCounts: []contracts.StatusCount{}}
	for _, row := range sums {
		rep.Rows = append(rep.Rows, *row)
	}
	sort.Slice(rep.Rows, func(i, j int) bool {
		a, b := rep.Rows[i], rep.Rows[j]
		return a.Month+a.EmployeeID+a.Category < b.Month+b.EmployeeID+b.Category
	})
	for st, n := range counts {
		rep.StatusCounts = append(rep.StatusCounts, contracts.StatusCount{Status: st, Count: n})
	}
	sort.Slice(rep.StatusCounts, func(i, j int) bool { return rep.StatusCounts[i].Status < rep.StatusCounts[j].Status })
	writeJSON(w, http.StatusOK, rep)
}
