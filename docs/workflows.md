# Workflow maps

Harborline Family Office and Cedar Bend Supply are fictional. The step counts and hours below are **illustrative design estimates** for those fictional processes. They are not measured savings from a live company, and they are not a claim about any employer.

The shape of each change is the same: the analyst stops retyping, the workbook or the dashboard calculates, and a person still approves anything that moves money or goes to the principal.

## What the estimates count

A "step" is a handoff or a manual action (download, rekey, email, check a cell by eye, file a PDF). Judgment steps stay. The hours are elapsed analyst time for one occurrence, not calendar time waiting on a manager.

| Process | Steps before | Steps after | Illustrative analyst time before | After | Steps removed |
| --- | ---: | ---: | --- | --- | ---: |
| Capital call | 14 | 4 | 6 hours | 45 minutes | 10 |
| Monthly management report | 18 | 5 | 2 days | 3 hours | 13 |
| Invoice / PO approval | 11 | 4 | 4 hours | 1 hour | 7 |

## 1. Capital call

Money leaves the family. The tracker can show unfunded commitment, due date, and cash need. It cannot decide to fund.

### Before

```mermaid
flowchart TD
    A["GP emails a capital-call PDF"] --> B["Analyst downloads the notice"]
    B --> C["Opens the commitment spreadsheet"]
    C --> D["Looks up unfunded by hand"]
    D --> E["Checks the cash balance in a second file"]
    E --> F["Emails the CIO"]
    F --> G["Waits, then forwards the thread to the controller"]
    G --> H["Rekeys the amount into a tracker"]
    H --> I["Adds a calendar reminder"]
    I --> J["Controller sends the wire"]
    J --> K["Analyst files the PDF"]
    K --> L["Updates called-to-date"]
    L --> M["Confirms back to the GP"]
    M --> N["Hopes the next deadline was written down"]
```

### After

```mermaid
flowchart TD
    A["Notice is saved to the SharePoint library"] --> B["Analyst adds one row to the call ledger"]
    B --> C["python -m fotoolkit run-all refreshes unfunded, status, and alerts"]
    C --> D["CIO approves or holds the call"]
    D --> E["Controller wires and marks the row paid"]
    E --> F["Next run moves the amount into called-to-date once the cash-flow row is added"]
```

The approval step is specified in [power-automate-design.md](power-automate-design.md). It is not a flow running in a tenant. On the sample ledger, as of 12 November 2026, this is the item the new path would have surfaced without anyone hunting through email: Gulf Prairie call CC-1041, $400,000, due 28 October, still open.

## 2. Monthly management report

Cedar Bend's close was a paste-up. The useful change is that bad rows are listed before anyone reads the margin.

### Before

```mermaid
flowchart TD
    A["GM exports sales"] --> B["AP exports purchases"]
    B --> C["Warehouse emails an inventory sheet"]
    C --> D["Analyst pastes all three into a workbook"]
    D --> E["Checks totals by eye"]
    E --> F["Types a variance explanation"]
    F --> G["Emails a PDF"]
    G --> H["Leadership replies with questions"]
    H --> I["Analyst rebuilds the same numbers in the reply"]
```

### After

```mermaid
flowchart TD
    A["Four source files land in data/sample or the drop folder"] --> B["Toolkit validates each row"]
    B --> C{"Any exception?"}
    C -->|Yes| D["Exception log is page one. Those rows are excluded from KPIs"]
    C -->|No| E["October P and L, variance, purchasing, and inventory"]
    D --> F["Analyst clears or corrects the source"]
    F --> B
    E --> G["Dashboard and HTML brief for the review meeting"]
    G --> H["GM and controller sign off"]
```

On this sample, nine rows fail a check and stay out of the October figures. Revenue is $462,000 against a $480,000 budget. The gross-margin rate is 34.54% versus 34.53% budget, so the dollar miss is volume, not the cost ratio. That sentence is the point of the automation: it is the same every month, and a person can trace it to the invoices.

Sign-off is a designed approval, not a deployed flow. See the management-report flow in the Power Automate note.

## 3. Invoice and PO approval

### Before

```mermaid
flowchart TD
    A["Requester emails AP"] --> B["AP retypes the invoice into a workbook"]
    B --> C["Manager approves by reply-all"]
    C --> D["Controller pays from the thread"]
    D --> E["PDF is dropped in a shared drive with an inconsistent name"]
```

### After

```mermaid
flowchart TD
    A["Invoice PDF and a list item are created"] --> B["Python validation must read Clear"]
    B -->|Not clear| C["Flow stops and emails AP. No payment task"]
    B -->|Clear| D{"Amount over the threshold?"}
    D -->|Yes| E["Manager approval, then controller"]
    D -->|No| F["Manager approval"]
    E --> G["Status becomes Ready to pay"]
    F --> G
    G --> H["Controller pays and sets status to Paid"]
```

The threshold in the design note is an illustrative $5,000. It is a parameter, not a number this sample calculated. Cedar Bend's purchasing file is the stand-in for the source extract: October has $305,400 of valid receipts and two rows the validator refuses (a negative amount, and a blank vendor).

## What stays manual on purpose

- The decision to fund a call.
- The investment-committee decision. Screening memos recommend a band. They do not place an order.
- Wiring cash and signing a report.
- Promoting a sentence in meeting notes into a task, unless it was written as an explicit action and a person approved the draft.
