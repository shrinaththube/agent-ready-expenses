// Package store is the expense repository. Submitted expenses cannot be
// modified through it; the only mutation after draft is a status transition,
// which always appends an audit entry in the same critical section.
package store

import (
	"errors"
	"fmt"
	"sort"
	"sync"

	"tally/policy/audit"
	"tally/policy/contracts"
)

var ErrNotFound = errors.New("expense not found")

// Memory is a goroutine-safe in-memory store.
type Memory struct {
	mu   sync.Mutex
	byID map[string]contracts.Expense
	seq  int
	Log  *audit.Log
}

func NewMemory() *Memory {
	return &Memory{byID: map[string]contracts.Expense{}, Log: &audit.Log{}}
}

// Create stores a new draft and assigns its id.
func (m *Memory) Create(e contracts.Expense) contracts.Expense {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.seq++
	e.ID = fmt.Sprintf("exp-%04d", m.seq)
	e.Status = contracts.ExpenseStatusDraft
	if e.Revision == 0 {
		e.Revision = 1
	}
	m.byID[e.ID] = e
	return e
}

func (m *Memory) Get(id string) (contracts.Expense, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	e, ok := m.byID[id]
	if !ok {
		return contracts.Expense{}, fmt.Errorf("%s: %w", id, ErrNotFound)
	}
	return e, nil
}

// List returns expenses sorted by id, filtered by employee and status when non-empty.
func (m *Memory) List(employeeID, status string) []contracts.Expense {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := []contracts.Expense{}
	for _, e := range m.byID {
		if (employeeID == "" || e.EmployeeID == employeeID) && (status == "" || string(e.Status) == status) {
			out = append(out, e)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// Transition runs workflow.Apply on the stored expense and appends the audit
// entry atomically. This is the only way a stored expense changes.
func (m *Memory) Transition(id string, f func(*contracts.Expense) (contracts.AuditEntry, error)) (contracts.Expense, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	e, ok := m.byID[id]
	if !ok {
		return contracts.Expense{}, fmt.Errorf("%s: %w", id, ErrNotFound)
	}
	entry, err := f(&e)
	if err != nil {
		return contracts.Expense{}, err
	}
	m.byID[id] = e
	m.Log.Append(entry)
	return e, nil
}

// PriorDaySpend sums base-currency minor units already committed by the same
// employee in the same category on the same date, excluding `excludeID`.
// Drafts and rejected expenses do not count.
func (m *Memory) PriorDaySpend(employeeID, category, date, excludeID string) int64 {
	m.mu.Lock()
	defer m.mu.Unlock()
	var total int64
	for _, e := range m.byID {
		if e.ID == excludeID || e.EmployeeID != employeeID || string(e.Category) != category || e.Date != date {
			continue
		}
		if e.Status == contracts.ExpenseStatusDraft || e.Status == contracts.ExpenseStatusRejected {
			continue
		}
		total += e.BaseAmount.AmountMinor
	}
	return total
}
