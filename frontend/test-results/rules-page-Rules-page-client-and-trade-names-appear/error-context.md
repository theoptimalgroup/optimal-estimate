# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rules-page.spec.ts >> Rules page >> client and trade names appear
- Location: e2e/rules-page.spec.ts:125:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('cell', { name: 'Atkinson McLeod' }).first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('cell', { name: 'Atkinson McLeod' }).first()

```

```yaml
- alert
- banner:
  - paragraph: Optimal Estimate Calculator
  - paragraph: Admin User · admin
  - button "Logout"
- complementary:
  - navigation:
    - link "Dashboard":
      - /url: /dashboard
    - link "Jobs":
      - /url: /jobs
    - link "Quotes":
      - /url: /quotes
    - link "Clients":
      - /url: /clients
    - link "Trades":
      - /url: /trades
    - link "Rules":
      - /url: /rules
- main:
  - heading "Rate Rules" [level=1]
  - paragraph: Pricing rules by client and trade. Global fallback applies when no match is found.
  - link "New Rule":
    - /url: /rules/new
  - textbox "Search client, alias, trade, version, or XLSX name"
  - combobox:
    - option "All clients" [selected]
    - option "Allen Heritage"
    - option "Apna Ghar"
    - option "Apnar Ghar"
    - option "Aspire"
    - option "Atkinson McLeod"
    - option "BPS"
    - option "Barnard & Marcus"
    - option "Barnard Marcus"
    - option "Bective"
    - option "Beresford Residential"
    - option "Berkshire Hathaway"
    - option "Blinkleys"
    - option "Blocshpere"
    - option "Blocsphere Property Management"
    - option "Bold & Reeces"
    - option "Bold and Reeces"
    - option "Brik Property Ltd"
    - option "Brinkley Estates"
    - option "Butler & Stag"
    - option "Butler & Stag LTD"
    - option "CAYSH"
    - option "CBRE"
    - option "CHISEL"
    - option "Campden Estates"
    - option "CareTech"
    - option "Caretech"
    - option "Carey Gardens Co-operative Ltd"
    - option "Carlisle"
    - option "Carter Gem"
    - option "Casa Londra"
    - option "Chamberland Residential"
    - option "Chelsea Heritage"
    - option "Chesterton"
    - option "Chisel"
    - option "Coopers of London"
    - option "Countrywide"
    - option "Daniel Watney"
    - option "Daniel Watney LLP"
    - option "Davies & Davies"
    - option "Dexters"
    - option "Direct Residential"
    - option "Dobbin and Sullivan Ltd"
    - option "Dolce Vita"
    - option "Douglas & Gordon"
    - option "Druce"
    - option "Easthaus"
    - option "Eddison White"
    - option "Emma's Estate Agents"
    - option "Evolve"
    - option "Evolve Housing"
    - option "Felicity J Lord"
    - option "First Union"
    - option "Fletchers"
    - option "Foster & Edward"
    - option "Foster & Edwards"
    - option "Frank Harris"
    - option "Garrett Whitelock"
    - option "Garrington"
    - option "Go View"
    - option "Hamptons"
    - option "Hamptons International"
    - option "Harrison Housing"
    - option "Hello Neighbour"
    - option "Henry Wiltshire"
    - option "Hestia"
    - option "Heywood & Partners"
    - option "Horniman"
    - option "ILGS Ltd T/A Newbrix"
    - option "ILGS Ltd TA Newbrix"
    - option "JC Living"
    - option "JD Group"
    - option "JDW"
    - option "JLL"
    - option "JSE"
    - option "JSE Property Management"
    - option "Jackson Stops & Staff"
    - option "Jacksons"
    - option "John D Wood"
    - option "Johns & CO"
    - option "Johns & Co"
    - option "KFH"
    - option "Key Property Consultants"
    - option "Kinleigh Folkard And Hayward (Block)"
    - option "Kinleigh Folkard and Hayward"
    - option "LDG"
    - option "Lamberts Chartered Surveyors"
    - option "Landstones"
    - option "Lee Abbey London"
    - option "Leo Estates Management"
    - option "Life Residential"
    - option "Lionsgate"
    - option "Lock Terrace"
    - option "Lurot Brand"
    - option "Lurot Brand DO NOT USE - BLACKLISTED"
    - option "MIH"
    - option "Maddison Brook"
    - option "Madison Brook"
    - option "Manage My Property"
    - option "Management Habitat Investments"
    - option "Marler & Marler"
    - option "Marsh & Parsons"
    - option "Martin & Co"
    - option "Mason & Fifth"
    - option "Mission Housing Limited"
    - option "NHS"
    - option "NHS Property Services"
    - option "Napier Watt"
    - option "Newbrix"
    - option "OIG"
    - option "Oliver Burn"
    - option "Oliver Burn Residential"
    - option "Oliver Jacques"
    - option "Oliver Jaques"
    - option "Orchard & Shipman"
    - option "Orlando Reid"
    - option "Portico"
    - option "Portico / Leaders"
    - option "Private Customer"
    - option "Property Maintenance & Management Services Ltd"
    - option "Purple Bricks"
    - option "Rampton Baseley"
    - option "Rampton Baseley Limited"
    - option "Rayners"
    - option "Referral Fee (5%)"
    - option "Regent Property"
    - option "Rendall & Rittner"
    - option "Right Now Residential"
    - option "Robertson Smith & Kempson"
    - option "Roupell Park"
    - option "Russell Simpson"
    - option "SW9"
    - option "SW9 Community Housing."
    - option "SWA Ltd"
    - option "Sigma / Simple Life"
    - option "Simple Life"
    - option "Sovreign Network Group"
    - option "Spurgeons"
    - option "Square Quarters"
    - option "Stirling Ackroyd"
    - option "Strangford Residence Management"
    - option "Strettons"
    - option "Strutt and Parker"
    - option "Swishbrook"
    - option "TLC"
    - option "TLC Estate Agents"
    - option "The Address"
    - option "Touchstone"
    - option "Trent Park Properties LLP"
    - option "Trotters Estates"
    - option "Victor Michael Limited"
    - option "WHR Property Management"
    - option "Warren Ltd"
    - option "Winkworth - Battersea"
    - option "Winkworth - Battersea, Clapham, Kennington, Pimlico & Westminster"
    - option "Winkworth - Newcross & Forest Hill"
    - option "Winkworth - Queens Park"
    - option "Winkworth - South Ken"
    - option "Winkworth - South Kensington"
  - combobox:
    - option "All trades" [selected]
    - option "Carpenter"
    - option "Doors, Windows & Locks"
    - option "Drains & Blockages"
    - option "Electrical"
    - option "Electrician"
    - option "Fencing & Decking"
    - option "Fire Certificate"
    - option "Gardening"
    - option "Gas Safe"
    - option "General Maintenance"
    - option "HVAC"
    - option "Handyman"
    - option "Leak Investigation"
    - option "Multi-trader"
    - option "Painter & Decorator"
    - option "Paths & Patios"
    - option "Plasterer & Tiller"
    - option "Plumber"
    - option "Plumbing"
    - option "Roof Investigation"
    - option "Roofer"
  - combobox:
    - option "All formula sources" [selected]
    - option "XLSX"
    - option "Simplified"
  - combobox:
    - option "All statuses"
    - option "Active" [selected]
    - option "Inactive"
  - textbox "Search by version"
  - table:
    - rowgroup:
      - row "Client Trade Formula Version Hourly Rate Half-Day Rate Day Rate Material Markup VAT Rate Active From Active To Status Actions":
        - columnheader "Client"
        - columnheader "Trade"
        - columnheader "Formula"
        - columnheader "Version"
        - columnheader "Hourly Rate"
        - columnheader "Half-Day Rate"
        - columnheader "Day Rate"
        - columnheader "Material Markup"
        - columnheader "VAT Rate"
        - columnheader "Active From"
        - columnheader "Active To"
        - columnheader "Status"
        - columnheader "Actions"
    - rowgroup:
      - row "Allen Heritage Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Carpenter"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/e9730239-0962-4628-a5cf-849e187bc2b2
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/e9730239-0962-4628-a5cf-849e187bc2b2
          - link "Edit rule":
            - /url: /rules/e9730239-0962-4628-a5cf-849e187bc2b2?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Doors, Windows & Locks"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/affcdf94-2390-4f8e-aaa1-f5166db9da91
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/affcdf94-2390-4f8e-aaa1-f5166db9da91
          - link "Edit rule":
            - /url: /rules/affcdf94-2390-4f8e-aaa1-f5166db9da91?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Drains & Blockages xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Drains & Blockages"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/51f432a6-e137-42a2-989e-170472685790
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/51f432a6-e137-42a2-989e-170472685790
          - link "Edit rule":
            - /url: /rules/51f432a6-e137-42a2-989e-170472685790?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Electrician xlsx xlsx-master-helper-1.7 £110.00 £138.60 £277.20 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Electrician"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/045abbf5-dc90-491b-81b9-c647ba47ed4d
        - cell "£110.00"
        - cell "£138.60"
        - cell "£277.20"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/045abbf5-dc90-491b-81b9-c647ba47ed4d
          - link "Edit rule":
            - /url: /rules/045abbf5-dc90-491b-81b9-c647ba47ed4d?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Fencing & Decking xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Fencing & Decking"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/eee4757d-b0d9-49ec-bbc1-0f9a59e14f4d
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/eee4757d-b0d9-49ec-bbc1-0f9a59e14f4d
          - link "Edit rule":
            - /url: /rules/eee4757d-b0d9-49ec-bbc1-0f9a59e14f4d?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Fire Certificate xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Fire Certificate"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/bcd9b347-64ee-4414-8ca7-e72807b57261
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/bcd9b347-64ee-4414-8ca7-e72807b57261
          - link "Edit rule":
            - /url: /rules/bcd9b347-64ee-4414-8ca7-e72807b57261?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Gardening xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Gardening"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/3f70b25b-2b55-4c4d-aa63-3b9a5a868e5a
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/3f70b25b-2b55-4c4d-aa63-3b9a5a868e5a
          - link "Edit rule":
            - /url: /rules/3f70b25b-2b55-4c4d-aa63-3b9a5a868e5a?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Gas Safe xlsx xlsx-master-helper-1.7 £120.00 £151.20 £302.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Gas Safe"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/daebbf38-76a8-4a80-b632-70919b234992
        - cell "£120.00"
        - cell "£151.20"
        - cell "£302.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/daebbf38-76a8-4a80-b632-70919b234992
          - link "Edit rule":
            - /url: /rules/daebbf38-76a8-4a80-b632-70919b234992?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Leak Investigation xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Leak Investigation"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/698dd6fb-aa0d-4d34-a2f2-4d1f317ba01c
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/698dd6fb-aa0d-4d34-a2f2-4d1f317ba01c
          - link "Edit rule":
            - /url: /rules/698dd6fb-aa0d-4d34-a2f2-4d1f317ba01c?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Multi-trader xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Multi-trader"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/88237a90-e8a2-4107-961a-2eacebb57191
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/88237a90-e8a2-4107-961a-2eacebb57191
          - link "Edit rule":
            - /url: /rules/88237a90-e8a2-4107-961a-2eacebb57191?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Painter & Decorator xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Painter & Decorator"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/f360ce1a-7491-4cc2-a02d-f531162f22e7
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/f360ce1a-7491-4cc2-a02d-f531162f22e7
          - link "Edit rule":
            - /url: /rules/f360ce1a-7491-4cc2-a02d-f531162f22e7?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Paths & Patios xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Paths & Patios"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/111510d4-e84f-4eeb-99ed-bc3524ff9b84
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/111510d4-e84f-4eeb-99ed-bc3524ff9b84
          - link "Edit rule":
            - /url: /rules/111510d4-e84f-4eeb-99ed-bc3524ff9b84?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Plasterer & Tiller xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Plasterer & Tiller"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/f21fdeae-e6c8-4d75-b35b-63b1704ebc65
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/f21fdeae-e6c8-4d75-b35b-63b1704ebc65
          - link "Edit rule":
            - /url: /rules/f21fdeae-e6c8-4d75-b35b-63b1704ebc65?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Plumber xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Plumber"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/fa62e260-1eb5-4130-9c27-aaf9266ae6af
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/fa62e260-1eb5-4130-9c27-aaf9266ae6af
          - link "Edit rule":
            - /url: /rules/fa62e260-1eb5-4130-9c27-aaf9266ae6af?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Roof Investigation xlsx xlsx-master-helper-1.7 £190.00 £239.40 £478.80 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Roof Investigation"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/e84d0147-cf2a-4021-9a94-6fbd63b28aa1
        - cell "£190.00"
        - cell "£239.40"
        - cell "£478.80"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/e84d0147-cf2a-4021-9a94-6fbd63b28aa1
          - link "Edit rule":
            - /url: /rules/e84d0147-cf2a-4021-9a94-6fbd63b28aa1?edit=1
          - button "Deactivate rule"
      - row "Allen Heritage Roofer xlsx xlsx-master-helper-1.7 £100.00 £126.00 £252.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Allen Heritage"
        - cell "Roofer"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/f3b5485e-4a7c-45df-aa1b-17d1b7035d7e
        - cell "£100.00"
        - cell "£126.00"
        - cell "£252.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/f3b5485e-4a7c-45df-aa1b-17d1b7035d7e
          - link "Edit rule":
            - /url: /rules/f3b5485e-4a7c-45df-aa1b-17d1b7035d7e?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Carpenter"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/2c260df2-f3cb-4d15-bab7-ac23c71404f9
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/2c260df2-f3cb-4d15-bab7-ac23c71404f9
          - link "Edit rule":
            - /url: /rules/2c260df2-f3cb-4d15-bab7-ac23c71404f9?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Doors, Windows & Locks"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/40fe058f-cee3-4a31-8683-45909d29bf85
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/40fe058f-cee3-4a31-8683-45909d29bf85
          - link "Edit rule":
            - /url: /rules/40fe058f-cee3-4a31-8683-45909d29bf85?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Drains & Blockages xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Drains & Blockages"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/a05984a6-8fcb-45b0-9253-36295c114bdb
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/a05984a6-8fcb-45b0-9253-36295c114bdb
          - link "Edit rule":
            - /url: /rules/a05984a6-8fcb-45b0-9253-36295c114bdb?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Electrician xlsx xlsx-master-helper-1.7 £110.00 £138.60 £277.20 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Electrician"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/c5ff6681-bd84-4f62-b1c4-464a2d80c8d7
        - cell "£110.00"
        - cell "£138.60"
        - cell "£277.20"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/c5ff6681-bd84-4f62-b1c4-464a2d80c8d7
          - link "Edit rule":
            - /url: /rules/c5ff6681-bd84-4f62-b1c4-464a2d80c8d7?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Fencing & Decking xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Fencing & Decking"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/c849fcaf-2724-4721-8fab-9ab75716122a
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/c849fcaf-2724-4721-8fab-9ab75716122a
          - link "Edit rule":
            - /url: /rules/c849fcaf-2724-4721-8fab-9ab75716122a?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Fire Certificate xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Fire Certificate"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/753d3f5b-8c2c-43bc-ae3d-f06708c7c963
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/753d3f5b-8c2c-43bc-ae3d-f06708c7c963
          - link "Edit rule":
            - /url: /rules/753d3f5b-8c2c-43bc-ae3d-f06708c7c963?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Gardening xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Gardening"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/2d9a476a-f386-4e2f-bb5a-75d614b22cf7
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/2d9a476a-f386-4e2f-bb5a-75d614b22cf7
          - link "Edit rule":
            - /url: /rules/2d9a476a-f386-4e2f-bb5a-75d614b22cf7?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Gas Safe xlsx xlsx-master-helper-1.7 £120.00 £151.20 £302.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Gas Safe"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/969c694c-41e0-4748-b46c-63374ddb1afd
        - cell "£120.00"
        - cell "£151.20"
        - cell "£302.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/969c694c-41e0-4748-b46c-63374ddb1afd
          - link "Edit rule":
            - /url: /rules/969c694c-41e0-4748-b46c-63374ddb1afd?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Leak Investigation xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Leak Investigation"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/694e03dc-adb2-4c7d-a4e0-f2f3d0be1119
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/694e03dc-adb2-4c7d-a4e0-f2f3d0be1119
          - link "Edit rule":
            - /url: /rules/694e03dc-adb2-4c7d-a4e0-f2f3d0be1119?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Multi-trader xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Multi-trader"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/c6c81f2c-1912-40de-b70d-88886e8bdf54
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/c6c81f2c-1912-40de-b70d-88886e8bdf54
          - link "Edit rule":
            - /url: /rules/c6c81f2c-1912-40de-b70d-88886e8bdf54?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Painter & Decorator xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Painter & Decorator"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/ea230736-c7da-45c1-9599-16b068451e38
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/ea230736-c7da-45c1-9599-16b068451e38
          - link "Edit rule":
            - /url: /rules/ea230736-c7da-45c1-9599-16b068451e38?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Paths & Patios xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Paths & Patios"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/12b4127a-0681-41b8-958e-b2b58aeb447d
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/12b4127a-0681-41b8-958e-b2b58aeb447d
          - link "Edit rule":
            - /url: /rules/12b4127a-0681-41b8-958e-b2b58aeb447d?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Plasterer & Tiller xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Plasterer & Tiller"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/36fcb834-1d3e-4f52-917c-6bb6415b9c03
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/36fcb834-1d3e-4f52-917c-6bb6415b9c03
          - link "Edit rule":
            - /url: /rules/36fcb834-1d3e-4f52-917c-6bb6415b9c03?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Plumber xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Plumber"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/a06467ae-f5e9-4d8c-bce2-2cc497f49cfc
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/a06467ae-f5e9-4d8c-bce2-2cc497f49cfc
          - link "Edit rule":
            - /url: /rules/a06467ae-f5e9-4d8c-bce2-2cc497f49cfc?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Roof Investigation xlsx xlsx-master-helper-1.7 £190.00 £239.40 £478.80 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Roof Investigation"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/0412e219-043a-4d37-9915-f4226d280d75
        - cell "£190.00"
        - cell "£239.40"
        - cell "£478.80"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/0412e219-043a-4d37-9915-f4226d280d75
          - link "Edit rule":
            - /url: /rules/0412e219-043a-4d37-9915-f4226d280d75?edit=1
          - button "Deactivate rule"
      - row "Apna Ghar Roofer xlsx xlsx-master-helper-1.7 £100.00 £126.00 £252.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apna Ghar"
        - cell "Roofer"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/7d202687-4eb3-4f8b-ac48-aaee2389ed49
        - cell "£100.00"
        - cell "£126.00"
        - cell "£252.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/7d202687-4eb3-4f8b-ac48-aaee2389ed49
          - link "Edit rule":
            - /url: /rules/7d202687-4eb3-4f8b-ac48-aaee2389ed49?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Carpenter"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/5c371089-ef73-4476-a2ef-a52ceea3dd50
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/5c371089-ef73-4476-a2ef-a52ceea3dd50
          - link "Edit rule":
            - /url: /rules/5c371089-ef73-4476-a2ef-a52ceea3dd50?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Doors, Windows & Locks"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/85b3fc76-172c-4b48-ab2d-a2510884771a
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/85b3fc76-172c-4b48-ab2d-a2510884771a
          - link "Edit rule":
            - /url: /rules/85b3fc76-172c-4b48-ab2d-a2510884771a?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Drains & Blockages xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Drains & Blockages"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/6e8b9e47-bff6-4dc0-ae2c-7f86d60c9907
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/6e8b9e47-bff6-4dc0-ae2c-7f86d60c9907
          - link "Edit rule":
            - /url: /rules/6e8b9e47-bff6-4dc0-ae2c-7f86d60c9907?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Electrician xlsx xlsx-master-helper-1.7 £110.00 £138.60 £277.20 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Electrician"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/f644593f-507a-4b6f-99b4-4e8736c20083
        - cell "£110.00"
        - cell "£138.60"
        - cell "£277.20"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/f644593f-507a-4b6f-99b4-4e8736c20083
          - link "Edit rule":
            - /url: /rules/f644593f-507a-4b6f-99b4-4e8736c20083?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Fencing & Decking xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Fencing & Decking"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/5e84687d-191e-4a44-a885-c176ea63d79e
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/5e84687d-191e-4a44-a885-c176ea63d79e
          - link "Edit rule":
            - /url: /rules/5e84687d-191e-4a44-a885-c176ea63d79e?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Fire Certificate xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Fire Certificate"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/96c8bf91-4d27-404a-9443-9dc53c58b214
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/96c8bf91-4d27-404a-9443-9dc53c58b214
          - link "Edit rule":
            - /url: /rules/96c8bf91-4d27-404a-9443-9dc53c58b214?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Gardening xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Gardening"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/5d737cbd-8d89-45e3-8190-3447795588a4
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/5d737cbd-8d89-45e3-8190-3447795588a4
          - link "Edit rule":
            - /url: /rules/5d737cbd-8d89-45e3-8190-3447795588a4?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Gas Safe xlsx xlsx-master-helper-1.7 £120.00 £151.20 £302.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Gas Safe"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/ca3382b6-7e14-4daf-82e6-d8f29450551b
        - cell "£120.00"
        - cell "£151.20"
        - cell "£302.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/ca3382b6-7e14-4daf-82e6-d8f29450551b
          - link "Edit rule":
            - /url: /rules/ca3382b6-7e14-4daf-82e6-d8f29450551b?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Leak Investigation xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Leak Investigation"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/7dba4ce8-cbc3-46ff-9271-728e0b182389
        - cell "£150.00"
        - cell "£189.00"
        - cell "£378.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/7dba4ce8-cbc3-46ff-9271-728e0b182389
          - link "Edit rule":
            - /url: /rules/7dba4ce8-cbc3-46ff-9271-728e0b182389?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Multi-trader xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Multi-trader"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/8771af7b-00c8-4e8d-aca2-ca7f3631cb95
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/8771af7b-00c8-4e8d-aca2-ca7f3631cb95
          - link "Edit rule":
            - /url: /rules/8771af7b-00c8-4e8d-aca2-ca7f3631cb95?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Painter & Decorator xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Painter & Decorator"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/cbf91783-63c2-43f3-ae98-b6ab7639f6cd
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/cbf91783-63c2-43f3-ae98-b6ab7639f6cd
          - link "Edit rule":
            - /url: /rules/cbf91783-63c2-43f3-ae98-b6ab7639f6cd?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Paths & Patios xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Paths & Patios"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/5b63681b-db34-4a04-bd68-00035f7c0d99
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/5b63681b-db34-4a04-bd68-00035f7c0d99
          - link "Edit rule":
            - /url: /rules/5b63681b-db34-4a04-bd68-00035f7c0d99?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Plasterer & Tiller xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Plasterer & Tiller"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/2ecce2f6-da21-4e5f-894f-28a1a6bea7b9
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/2ecce2f6-da21-4e5f-894f-28a1a6bea7b9
          - link "Edit rule":
            - /url: /rules/2ecce2f6-da21-4e5f-894f-28a1a6bea7b9?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Plumber xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Plumber"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/a3cf50cc-2463-43fa-b1e9-79b73e2b49fd
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/a3cf50cc-2463-43fa-b1e9-79b73e2b49fd
          - link "Edit rule":
            - /url: /rules/a3cf50cc-2463-43fa-b1e9-79b73e2b49fd?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Roof Investigation xlsx xlsx-master-helper-1.7 £190.00 £239.40 £478.80 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Roof Investigation"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/7bd78605-c07e-4289-86a0-0a97fd9655b2
        - cell "£190.00"
        - cell "£239.40"
        - cell "£478.80"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/7bd78605-c07e-4289-86a0-0a97fd9655b2
          - link "Edit rule":
            - /url: /rules/7bd78605-c07e-4289-86a0-0a97fd9655b2?edit=1
          - button "Deactivate rule"
      - row "Apnar Ghar Roofer xlsx xlsx-master-helper-1.7 £100.00 £126.00 £252.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Apnar Ghar"
        - cell "Roofer"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/ad40cf24-8b99-48b3-ba5f-24f4e28619f9
        - cell "£100.00"
        - cell "£126.00"
        - cell "£252.00"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/ad40cf24-8b99-48b3-ba5f-24f4e28619f9
          - link "Edit rule":
            - /url: /rules/ad40cf24-8b99-48b3-ba5f-24f4e28619f9?edit=1
          - button "Deactivate rule"
      - row "Aspire Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Aspire"
        - cell "Carpenter"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/cefa3912-15b4-4cbb-bf9c-436e25de6868
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/cefa3912-15b4-4cbb-bf9c-436e25de6868
          - link "Edit rule":
            - /url: /rules/cefa3912-15b4-4cbb-bf9c-436e25de6868?edit=1
          - button "Deactivate rule"
      - row "Aspire Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule":
        - cell "Aspire"
        - cell "Doors, Windows & Locks"
        - cell "xlsx"
        - cell "xlsx-master-helper-1.7":
          - link "xlsx-master-helper-1.7":
            - /url: /rules/7b739499-24e1-4a0a-a255-2914f03b8056
        - cell "£95.00"
        - cell "£119.70"
        - cell "£239.40"
        - cell "20%"
        - cell "20%"
        - cell "2024-01-01"
        - cell "—"
        - cell "Active"
        - cell "View rule Edit rule Deactivate rule":
          - link "View rule":
            - /url: /rules/7b739499-24e1-4a0a-a255-2914f03b8056
          - link "Edit rule":
            - /url: /rules/7b739499-24e1-4a0a-a255-2914f03b8056?edit=1
          - button "Deactivate rule"
  - text: 2528 rules
  - button "Previous" [disabled]
  - text: Page 1 of 51
  - button "Next"
```

# Test source

```ts
  29  |   const clients = (await (await request.get(`${API}/api/v1/clients`, { headers })).json()).data;
  30  |   const trades = (await (await request.get(`${API}/api/v1/trades`, { headers })).json()).data;
  31  |   return { clients, trades };
  32  | }
  33  | 
  34  | test.describe("Rules page", () => {
  35  |   test("admin sees actions", async ({ page }) => {
  36  |     await login(page, USERS.admin.email, USERS.admin.password);
  37  |     await page.goto("/rules");
  38  | 
  39  |     await expect(page.getByRole("link", { name: "New Rule" })).toBeVisible();
  40  |     await expect(page.getByRole("link", { name: "View rule" }).first()).toBeVisible();
  41  |     await expect(page.getByRole("link", { name: "Edit rule" }).first()).toBeVisible();
  42  |     await expect(page.getByRole("button", { name: /Deactivate rule|Activate rule/ }).first()).toBeVisible();
  43  |   });
  44  | 
  45  |   test("estimator does not see edit actions", async ({ page }) => {
  46  |     await login(page, USERS.estimator.email, USERS.estimator.password);
  47  |     await page.goto("/rules");
  48  | 
  49  |     await expect(page.getByRole("link", { name: "View rule" }).first()).toBeVisible();
  50  |     await expect(page.getByRole("link", { name: "New Rule" })).toHaveCount(0);
  51  |     await expect(page.getByRole("link", { name: "Edit rule" })).toHaveCount(0);
  52  |     await expect(page.getByRole("button", { name: /Deactivate rule|Activate rule/ })).toHaveCount(0);
  53  |   });
  54  | 
  55  |   test("filters update table", async ({ page, request }) => {
  56  |     const token = await apiLogin(request, USERS.admin.email, USERS.admin.password);
  57  |     const { clients, trades } = await fetchMasterData(request, token);
  58  |     const atkinson = clients.find((c: { name: string }) => c.name === "Atkinson McLeod");
  59  |     const multiTrader = trades.find((t: { name: string }) => t.name === "Multi-trader");
  60  | 
  61  |     await login(page, USERS.admin.email, USERS.admin.password);
  62  |     await page.goto("/rules");
  63  |     await expect(page.getByRole("link", { name: "View rule" }).first()).toBeVisible();
  64  | 
  65  |     const dataRows = page.locator("tbody tr").filter({ has: page.getByRole("link", { name: "View rule" }) });
  66  |     const initialCount = await dataRows.count();
  67  |     expect(initialCount).toBeGreaterThan(1);
  68  | 
  69  |     await page.locator("select").nth(0).selectOption(atkinson.id);
  70  |     await expect(page.getByRole("cell", { name: "Atkinson McLeod" }).first()).toBeVisible();
  71  |     await expect(page.getByRole("cell", { name: "Napier Watt" })).toHaveCount(0);
  72  |     const clientFilteredCount = await dataRows.count();
  73  |     expect(clientFilteredCount).toBeLessThan(initialCount);
  74  | 
  75  |     await page.locator("select").nth(1).selectOption(multiTrader.id);
  76  |     await expect(page.getByRole("cell", { name: "Carpenter" })).toHaveCount(0);
  77  |     const tradeFilteredCount = await dataRows.count();
  78  |     expect(tradeFilteredCount).toBeLessThan(clientFilteredCount);
  79  | 
  80  |     await page.locator("select").nth(0).selectOption("");
  81  |     await page.locator("select").nth(1).selectOption("");
  82  |     await page.getByPlaceholder("Search by version").fill("global-fallback");
  83  |     await expect(page.getByRole("link", { name: "global-fallback-1.0" })).toBeVisible();
  84  |     await expect(dataRows).toHaveCount(1);
  85  |   });
  86  | 
  87  |   test("empty state renders", async ({ page }) => {
  88  |     await page.route("**/api/v1/rules**", async (route) => {
  89  |       await route.fulfill({
  90  |         status: 200,
  91  |         contentType: "application/json",
  92  |         body: JSON.stringify({
  93  |           success: true,
  94  |           data: [
  95  |             {
  96  |               id: "00000000-0000-0000-0000-000000000001",
  97  |               client_id: null,
  98  |               trade_id: null,
  99  |               client_name: null,
  100 |               trade_name: null,
  101 |               version: "global-fallback-1.0",
  102 |               hourly_rate: "65.00",
  103 |               half_day_rate: "240.00",
  104 |               day_rate: "450.00",
  105 |               material_markup_type: "percentage",
  106 |               material_markup_value: "10.00",
  107 |               vat_rate: "20.00",
  108 |               active_from: "2024-01-01",
  109 |               active_to: null,
  110 |               is_active: true,
  111 |             },
  112 |           ],
  113 |           meta: { page: 1, page_size: 50, total: 1, total_pages: 1, client_specific_count: 0 },
  114 |         }),
  115 |       });
  116 |     });
  117 | 
  118 |     await login(page, USERS.admin.email, USERS.admin.password);
  119 |     await page.goto("/rules");
  120 | 
  121 |     await expect(page.getByText(EMPTY_STATE_MESSAGE)).toBeVisible();
  122 |     await expect(page.locator("tbody td").filter({ hasText: /^Global$/ }).first()).toBeVisible();
  123 |   });
  124 | 
  125 |   test("client and trade names appear", async ({ page }) => {
  126 |     await login(page, USERS.admin.email, USERS.admin.password);
  127 |     await page.goto("/rules");
  128 | 
> 129 |     await expect(page.getByRole("cell", { name: "Atkinson McLeod" }).first()).toBeVisible();
      |                                                                               ^ Error: expect(locator).toBeVisible() failed
  130 |     await expect(page.getByRole("cell", { name: "Multi-trader" }).first()).toBeVisible();
  131 |     await expect(page.locator("tbody td").filter({ hasText: /^Global$/ }).first()).toBeVisible();
  132 |     await expect(page.locator("tbody td").filter({ hasText: /^All trades$/ }).first()).toBeVisible();
  133 |   });
  134 | 
  135 |   test("active and inactive status displays correctly", async ({ page }) => {
  136 |     await login(page, USERS.admin.email, USERS.admin.password);
  137 |     await page.goto("/rules");
  138 | 
  139 |     const activeBadges = page.locator("tbody span").filter({ hasText: /^Active$/ });
  140 |     const inactiveBadges = page.locator("tbody span").filter({ hasText: /^Inactive$/ });
  141 | 
  142 |     await expect(activeBadges.first()).toBeVisible();
  143 |     await expect(inactiveBadges).toHaveCount(0);
  144 | 
  145 |     await page.locator("select").nth(2).selectOption("false");
  146 |     await expect(inactiveBadges.first()).toBeVisible();
  147 |     await expect(activeBadges).toHaveCount(0);
  148 | 
  149 |     await page.locator("select").nth(2).selectOption("all");
  150 |     await expect(activeBadges.first()).toBeVisible();
  151 |     await expect(inactiveBadges.first()).toBeVisible();
  152 |   });
  153 | });
  154 | 
  155 | test.describe("Rules API", () => {
  156 |   test("list includes client_name, trade_name, and status filters", async ({ request }) => {
  157 |     const token = await apiLogin(request, USERS.admin.email, USERS.admin.password);
  158 |     const headers = { Authorization: `Bearer ${token}` };
  159 | 
  160 |     const body = await (await request.get(`${API}/api/v1/rules`, { headers })).json();
  161 |     const named = body.data.find((r: { client_name?: string | null }) => r.client_name);
  162 |     expect(named.client_name).toBeTruthy();
  163 |     expect(named.trade_name).toBeTruthy();
  164 |     expect(body.data.find((r: { client_name: null }) => r.client_name === null)).toBeTruthy();
  165 | 
  166 |     const active = await (await request.get(`${API}/api/v1/rules?is_active=true`, { headers })).json();
  167 |     expect(active.data.every((r: { is_active: boolean }) => r.is_active)).toBe(true);
  168 | 
  169 |     const inactive = await (await request.get(`${API}/api/v1/rules?is_active=false`, { headers })).json();
  170 |     if (inactive.data.length > 0) {
  171 |       expect(inactive.data.every((r: { is_active: boolean }) => !r.is_active)).toBe(true);
  172 |     }
  173 |   });
  174 | });
  175 | 
```