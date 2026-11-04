# 0003: Submitted expenses are immutable; corrections are revisions

Status: accepted

Once an expense leaves `draft` its fields never change. A correction creates a new expense with `revision = n+1` and `revision_of` pointing back along the chain (the original or the revision it corrects), and that revision goes through the workflow again. Status changes are the only mutation after submit, and each appends an append-only audit entry in the same critical section (`store.Transition`).

Why: approvers and auditors must be able to trust that what was approved is what was submitted. Editing in place would invalidate approvals silently.
