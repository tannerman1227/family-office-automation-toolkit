# Power Automate, SharePoint, and Power Apps

These are designs. They are not flows in a Microsoft 365 tenant, they are not SharePoint lists that exist anywhere but on this page, and there is no Power App in this repo. Building them requires a tenant, connectors, and an owner for permissions. The Python toolkit is the part that actually runs.

The designs assume the calculation stays in the toolkit. A cloud flow is a good way to notify, collect an approval, and write a status. It is a poor place to re-implement unfunded commitment, a screening score, or a gross-margin variance. Those rules already have tests.

Two ways to connect them, neither of which is built here:

- **File drop.** Someone runs `python -m fotoolkit run-all` on a private machine and copies the workbook to a SharePoint library. A cloud flow triggers on the new file and starts the approval. The flow never sees the source ledger.
- **List as the inbox.** Staff enter notices and invoices in SharePoint. A scheduled desktop flow, or a person, exports the lists, the toolkit runs, and the results are written back as status columns. The export step is the control. Do not let a flow mark a call "paid" because a file arrived.

## SharePoint lists

Site: a private site, not the company's open intranet. Illustrative name: `Harborline Operations`.

### Capital calls

| Column | Type | Notes |
| --- | --- | --- |
| Title | Single line | Call id, for example CC-1041 |
| Fund | Choice or lookup | The six sample funds, maintained as a Fund list |
| Amount | Currency | USD, 0 decimals |
| Notice date | Date | |
| Due date | Date | |
| Purpose | Single line | |
| Ledger status | Choice | open, paid |
| Approval | Choice | Pending, Approved, Held |
| Approver comment | Multiple lines | Required when Held |
| Notice | Hyperlink or file | The PDF. The flow does not parse it |

### Reporting deadlines

| Column | Type | Notes |
| --- | --- | --- |
| Title | Single line | Deadline id |
| Fund | Lookup | |
| Report | Single line | |
| Period | Single line | |
| Due date | Date | |
| Received | Date | Blank until the file is in the library |
| Status | Choice | pending, received |

### Tasks

| Column | Type | Notes |
| --- | --- | --- |
| Title | Single line | |
| Owner | Person | |
| Due date | Date | |
| Status | Choice | open, done |
| Source | Choice | operations, AI summary — human approved |
| Related | Single line | Call id, deadline id, or note filename |

An item with source "AI summary — human approved" is created only after the Review page in the toolkit, or an equivalent approval in the list, is completed. The flow must not create it from the raw note.

### Invoices

| Column | Type | Notes |
| --- | --- | --- |
| Title | Single line | Invoice or PO id |
| Vendor | Single line | Required |
| Amount | Currency | Must be greater than zero to leave Draft |
| Validation status | Choice | Draft, Clear, Exception |
| Approval | Choice | Pending, Approved, Rejected |
| Paid | Yes/No | Controller only |

Validation status is set by a person after they have read the toolkit exception log, or by a desktop flow that reads `fact_exception` and refuses to set Clear when the id appears there. A cloud flow that sets Clear on its own, with no check, defeats the control.

## Flow A — Capital call approval

| | |
| --- | --- |
| Trigger | When a file is created in library `Capital Call Notices` |
| Action | Create a Capital calls item. Fund, amount, and due date are properties the analyst fills on the upload form. The PDF is attached, not parsed. |
| Action | Start and wait for an approval. Assign to the CIO role. Title includes the fund, the amount, and the due date. |
| If approved | Set Approval to Approved. Create a Tasks item for the controller: "Send wire for {call id}", due on the call's due date. Post a message to the private leadership channel. |
| If rejected | Set Approval to Held. The comment is required. Email the analyst. Do not create a payment task. |
| Parallel condition | If Due date is before today, flag the Teams message as high priority. This catches the case the sample already contains. |
| Failure | If the approval times out, leave Approval as Pending and email the CIO once. Do not default to Approved. |

What this flow does not do: compute unfunded commitment, update called-to-date, or decide the family can afford the call. Those stay in the workbook. After the wire is sent, a person adds the contribution to `cashflows.csv` and sets the ledger status to paid. The next toolkit run reconciles called-to-date to the cash flows and will alert if they disagree.

## Flow B — Monthly report sign-off

| | |
| --- | --- |
| Trigger | When a file is created in library `Management Reports` and the name contains `management_report` |
| Action | Post the file link to the operating-company channel with the sentence from `outputs/management/monthly_report.html`, pasted by the analyst or taken from the HTML the toolkit already wrote. |
| Action | Start and wait for an approval, first the general manager, then the controller, in sequence. |
| If both approve | Move the file to `Management Reports/Signed/{year-month}` and set a library column Signed to Yes. |
| If either rejects | Leave the file in place, create a Tasks item with the comment, and do not mark it signed. |
| Failure | A timeout leaves the file unsigned. There is no auto-approve. |

The recurrence people usually want ("6:00 on the first business day") can remind the analyst to run the toolkit. It should not pretend the cloud flow produced the numbers. A reminder flow is enough:

| | |
| --- | --- |
| Trigger | Recurrence, monthly, day 1, 07:00, Central time |
| Action | Condition on weekday. If the first is a weekend, the reminder still fires and the analyst runs the close on the next business morning. Getting that calendar perfect is not worth a custom connector. |
| Action | Post "October-style close: run the toolkit, clear the exception log, drop the workbook in Management Reports." |

## Flow C — Invoice approval

| | |
| --- | --- |
| Trigger | When an item is created in Invoices |
| Condition | Validation status equals Clear. If it does not, email AP and stop. |
| Condition | Amount greater than 5000 uses two approvers (manager, then controller). Otherwise the manager only. The 5000 is an illustrative parameter in this design, not a figure from the sample P&L. |
| If approved | Set Approval to Approved and create a payment task for the controller. |
| If rejected | Set Approval to Rejected and email the requester with the comment. |
| Failure | Same as the other flows: no default approval. |

## Power Apps, as a spec only

A canvas app on the same lists would be the phone surface. Three screens:

1. **My tasks.** Gallery of Tasks where Owner is `User().Email` and Status is open, sorted by due date.
2. **Capital call.** View of the selected call: amount, due date, fund, and the approval buttons. The unfunded balance is displayed from a column the toolkit wrote back, with the as-of date next to it, so the app does not recalculate it.
3. **Invoice.** Form to create an item. Amount and vendor are required. Validation status defaults to Draft. There is no Pay button on this screen. Payment stays with the controller after Flow C.

The app is not in this repository. Publishing it is a tenant change, with the same permission model as the lists.

## What has to be true before any of this is turned on

- The sample has been replaced, outside git, with real lists, and one month has been tied to the old spreadsheet.
- The approval assignees are roles, not a single person's mailbox, so a vacation does not stall a wire.
- The family has decided whether notes may leave the tenant. Flow A in this design does not send document text to a model. If someone later adds AI Builder to read the PDF, that is a separate decision, and a person still checks the amount before the approval starts.
- There is a named owner for the flows, a solution export, and a short note of what the flow will not do. The note above is the start of that.
