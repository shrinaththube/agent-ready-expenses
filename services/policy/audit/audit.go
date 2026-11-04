// Package audit holds the append-only audit log. There is intentionally no
// update or delete API.
package audit

import (
	"sync"

	"tally/policy/contracts"
)

// Log is an in-memory append-only log.
type Log struct {
	mu      sync.Mutex
	entries []contracts.AuditEntry
}

// Append adds an entry and assigns its sequence number.
func (l *Log) Append(e contracts.AuditEntry) contracts.AuditEntry {
	l.mu.Lock()
	defer l.mu.Unlock()
	e.Seq = int64(len(l.entries) + 1)
	l.entries = append(l.entries, e)
	return e
}

// For returns a copy of the entries for one expense, oldest first.
func (l *Log) For(expenseID string) []contracts.AuditEntry {
	l.mu.Lock()
	defer l.mu.Unlock()
	out := []contracts.AuditEntry{}
	for _, e := range l.entries {
		if e.ExpenseID == expenseID {
			out = append(out, e)
		}
	}
	return out
}
