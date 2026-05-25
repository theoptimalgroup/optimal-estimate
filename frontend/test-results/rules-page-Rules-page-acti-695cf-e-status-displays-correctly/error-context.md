# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rules-page.spec.ts >> Rules page >> active and inactive status displays correctly
- Location: e2e/rules-page.spec.ts:135:7

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 120000ms exceeded.
Call log:
  - waiting for locator('select').nth(2)
    - locator resolved to <select class="rounded-md border px-3 py-2 text-sm">…</select>
  - attempting select option action
    2 × waiting for element to be visible and enabled
      - did not find some options
    - retrying select option action
    - waiting 20ms
    2 × waiting for element to be visible and enabled
      - did not find some options
    - retrying select option action
      - waiting 100ms
    236 × waiting for element to be visible and enabled
        - did not find some options
      - retrying select option action
        - waiting 500ms

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - alert [ref=e2]
  - generic [ref=e3]:
    - banner [ref=e4]:
      - generic [ref=e5]:
        - generic [ref=e6]:
          - paragraph [ref=e7]: Optimal Estimate Calculator
          - paragraph [ref=e8]: Admin User · admin
        - button "Logout" [ref=e9] [cursor=pointer]
    - generic [ref=e10]:
      - complementary [ref=e11]:
        - navigation [ref=e12]:
          - link "Dashboard" [ref=e13] [cursor=pointer]:
            - /url: /dashboard
          - link "Jobs" [ref=e14] [cursor=pointer]:
            - /url: /jobs
          - link "Quotes" [ref=e15] [cursor=pointer]:
            - /url: /quotes
          - link "Clients" [ref=e16] [cursor=pointer]:
            - /url: /clients
          - link "Trades" [ref=e17] [cursor=pointer]:
            - /url: /trades
          - link "Rules" [ref=e18] [cursor=pointer]:
            - /url: /rules
      - main [ref=e19]:
        - generic [ref=e20]:
          - generic [ref=e21]:
            - generic [ref=e22]:
              - heading "Rate Rules" [level=1] [ref=e23]
              - paragraph [ref=e24]: Pricing rules by client and trade. Global fallback applies when no match is found.
            - link "New Rule" [ref=e25] [cursor=pointer]:
              - /url: /rules/new
          - generic [ref=e26]:
            - textbox "Search client, alias, trade, version, or XLSX name" [ref=e27]
            - combobox [ref=e28]:
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
            - combobox [ref=e29]:
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
            - combobox [ref=e30]:
              - option "All formula sources" [selected]
              - option "XLSX"
              - option "Simplified"
            - combobox [ref=e31]:
              - option "All statuses"
              - option "Active" [selected]
              - option "Inactive"
            - textbox "Search by version" [ref=e32]
          - table [ref=e34]:
            - rowgroup [ref=e35]:
              - row "Client Trade Formula Version Hourly Rate Half-Day Rate Day Rate Material Markup VAT Rate Active From Active To Status Actions" [ref=e36]:
                - columnheader "Client" [ref=e37]
                - columnheader "Trade" [ref=e38]
                - columnheader "Formula" [ref=e39]
                - columnheader "Version" [ref=e40]
                - columnheader "Hourly Rate" [ref=e41]
                - columnheader "Half-Day Rate" [ref=e42]
                - columnheader "Day Rate" [ref=e43]
                - columnheader "Material Markup" [ref=e44]
                - columnheader "VAT Rate" [ref=e45]
                - columnheader "Active From" [ref=e46]
                - columnheader "Active To" [ref=e47]
                - columnheader "Status" [ref=e48]
                - columnheader "Actions" [ref=e49]
            - rowgroup [ref=e50]:
              - row "Allen Heritage Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e51]:
                - cell "Allen Heritage" [ref=e52]
                - cell "Carpenter" [ref=e53]
                - cell "xlsx" [ref=e54]
                - cell "xlsx-master-helper-1.7" [ref=e55]:
                  - link "xlsx-master-helper-1.7" [ref=e56] [cursor=pointer]:
                    - /url: /rules/e9730239-0962-4628-a5cf-849e187bc2b2
                - cell "£95.00" [ref=e57]
                - cell "£119.70" [ref=e58]
                - cell "£239.40" [ref=e59]
                - cell "20%" [ref=e60]
                - cell "20%" [ref=e61]
                - cell "2024-01-01" [ref=e62]
                - cell "—" [ref=e63]
                - cell "Active" [ref=e64]
                - cell "View rule Edit rule Deactivate rule" [ref=e65]:
                  - generic [ref=e66]:
                    - link "View rule" [ref=e67] [cursor=pointer]:
                      - /url: /rules/e9730239-0962-4628-a5cf-849e187bc2b2
                    - link "Edit rule" [ref=e68] [cursor=pointer]:
                      - /url: /rules/e9730239-0962-4628-a5cf-849e187bc2b2?edit=1
                    - button "Deactivate rule" [ref=e69] [cursor=pointer]
              - row "Allen Heritage Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e70]:
                - cell "Allen Heritage" [ref=e71]
                - cell "Doors, Windows & Locks" [ref=e72]
                - cell "xlsx" [ref=e73]
                - cell "xlsx-master-helper-1.7" [ref=e74]:
                  - link "xlsx-master-helper-1.7" [ref=e75] [cursor=pointer]:
                    - /url: /rules/affcdf94-2390-4f8e-aaa1-f5166db9da91
                - cell "£95.00" [ref=e76]
                - cell "£119.70" [ref=e77]
                - cell "£239.40" [ref=e78]
                - cell "20%" [ref=e79]
                - cell "20%" [ref=e80]
                - cell "2024-01-01" [ref=e81]
                - cell "—" [ref=e82]
                - cell "Active" [ref=e83]
                - cell "View rule Edit rule Deactivate rule" [ref=e84]:
                  - generic [ref=e85]:
                    - link "View rule" [ref=e86] [cursor=pointer]:
                      - /url: /rules/affcdf94-2390-4f8e-aaa1-f5166db9da91
                    - link "Edit rule" [ref=e87] [cursor=pointer]:
                      - /url: /rules/affcdf94-2390-4f8e-aaa1-f5166db9da91?edit=1
                    - button "Deactivate rule" [ref=e88] [cursor=pointer]
              - row "Allen Heritage Drains & Blockages xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e89]:
                - cell "Allen Heritage" [ref=e90]
                - cell "Drains & Blockages" [ref=e91]
                - cell "xlsx" [ref=e92]
                - cell "xlsx-master-helper-1.7" [ref=e93]:
                  - link "xlsx-master-helper-1.7" [ref=e94] [cursor=pointer]:
                    - /url: /rules/51f432a6-e137-42a2-989e-170472685790
                - cell "£150.00" [ref=e95]
                - cell "£189.00" [ref=e96]
                - cell "£378.00" [ref=e97]
                - cell "20%" [ref=e98]
                - cell "20%" [ref=e99]
                - cell "2024-01-01" [ref=e100]
                - cell "—" [ref=e101]
                - cell "Active" [ref=e102]
                - cell "View rule Edit rule Deactivate rule" [ref=e103]:
                  - generic [ref=e104]:
                    - link "View rule" [ref=e105] [cursor=pointer]:
                      - /url: /rules/51f432a6-e137-42a2-989e-170472685790
                    - link "Edit rule" [ref=e106] [cursor=pointer]:
                      - /url: /rules/51f432a6-e137-42a2-989e-170472685790?edit=1
                    - button "Deactivate rule" [ref=e107] [cursor=pointer]
              - row "Allen Heritage Electrician xlsx xlsx-master-helper-1.7 £110.00 £138.60 £277.20 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e108]:
                - cell "Allen Heritage" [ref=e109]
                - cell "Electrician" [ref=e110]
                - cell "xlsx" [ref=e111]
                - cell "xlsx-master-helper-1.7" [ref=e112]:
                  - link "xlsx-master-helper-1.7" [ref=e113] [cursor=pointer]:
                    - /url: /rules/045abbf5-dc90-491b-81b9-c647ba47ed4d
                - cell "£110.00" [ref=e114]
                - cell "£138.60" [ref=e115]
                - cell "£277.20" [ref=e116]
                - cell "20%" [ref=e117]
                - cell "20%" [ref=e118]
                - cell "2024-01-01" [ref=e119]
                - cell "—" [ref=e120]
                - cell "Active" [ref=e121]
                - cell "View rule Edit rule Deactivate rule" [ref=e122]:
                  - generic [ref=e123]:
                    - link "View rule" [ref=e124] [cursor=pointer]:
                      - /url: /rules/045abbf5-dc90-491b-81b9-c647ba47ed4d
                    - link "Edit rule" [ref=e125] [cursor=pointer]:
                      - /url: /rules/045abbf5-dc90-491b-81b9-c647ba47ed4d?edit=1
                    - button "Deactivate rule" [ref=e126] [cursor=pointer]
              - row "Allen Heritage Fencing & Decking xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e127]:
                - cell "Allen Heritage" [ref=e128]
                - cell "Fencing & Decking" [ref=e129]
                - cell "xlsx" [ref=e130]
                - cell "xlsx-master-helper-1.7" [ref=e131]:
                  - link "xlsx-master-helper-1.7" [ref=e132] [cursor=pointer]:
                    - /url: /rules/eee4757d-b0d9-49ec-bbc1-0f9a59e14f4d
                - cell "£95.00" [ref=e133]
                - cell "£119.70" [ref=e134]
                - cell "£239.40" [ref=e135]
                - cell "20%" [ref=e136]
                - cell "20%" [ref=e137]
                - cell "2024-01-01" [ref=e138]
                - cell "—" [ref=e139]
                - cell "Active" [ref=e140]
                - cell "View rule Edit rule Deactivate rule" [ref=e141]:
                  - generic [ref=e142]:
                    - link "View rule" [ref=e143] [cursor=pointer]:
                      - /url: /rules/eee4757d-b0d9-49ec-bbc1-0f9a59e14f4d
                    - link "Edit rule" [ref=e144] [cursor=pointer]:
                      - /url: /rules/eee4757d-b0d9-49ec-bbc1-0f9a59e14f4d?edit=1
                    - button "Deactivate rule" [ref=e145] [cursor=pointer]
              - row "Allen Heritage Fire Certificate xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e146]:
                - cell "Allen Heritage" [ref=e147]
                - cell "Fire Certificate" [ref=e148]
                - cell "xlsx" [ref=e149]
                - cell "xlsx-master-helper-1.7" [ref=e150]:
                  - link "xlsx-master-helper-1.7" [ref=e151] [cursor=pointer]:
                    - /url: /rules/bcd9b347-64ee-4414-8ca7-e72807b57261
                - cell "£150.00" [ref=e152]
                - cell "£189.00" [ref=e153]
                - cell "£378.00" [ref=e154]
                - cell "20%" [ref=e155]
                - cell "20%" [ref=e156]
                - cell "2024-01-01" [ref=e157]
                - cell "—" [ref=e158]
                - cell "Active" [ref=e159]
                - cell "View rule Edit rule Deactivate rule" [ref=e160]:
                  - generic [ref=e161]:
                    - link "View rule" [ref=e162] [cursor=pointer]:
                      - /url: /rules/bcd9b347-64ee-4414-8ca7-e72807b57261
                    - link "Edit rule" [ref=e163] [cursor=pointer]:
                      - /url: /rules/bcd9b347-64ee-4414-8ca7-e72807b57261?edit=1
                    - button "Deactivate rule" [ref=e164] [cursor=pointer]
              - row "Allen Heritage Gardening xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e165]:
                - cell "Allen Heritage" [ref=e166]
                - cell "Gardening" [ref=e167]
                - cell "xlsx" [ref=e168]
                - cell "xlsx-master-helper-1.7" [ref=e169]:
                  - link "xlsx-master-helper-1.7" [ref=e170] [cursor=pointer]:
                    - /url: /rules/3f70b25b-2b55-4c4d-aa63-3b9a5a868e5a
                - cell "£95.00" [ref=e171]
                - cell "£119.70" [ref=e172]
                - cell "£239.40" [ref=e173]
                - cell "20%" [ref=e174]
                - cell "20%" [ref=e175]
                - cell "2024-01-01" [ref=e176]
                - cell "—" [ref=e177]
                - cell "Active" [ref=e178]
                - cell "View rule Edit rule Deactivate rule" [ref=e179]:
                  - generic [ref=e180]:
                    - link "View rule" [ref=e181] [cursor=pointer]:
                      - /url: /rules/3f70b25b-2b55-4c4d-aa63-3b9a5a868e5a
                    - link "Edit rule" [ref=e182] [cursor=pointer]:
                      - /url: /rules/3f70b25b-2b55-4c4d-aa63-3b9a5a868e5a?edit=1
                    - button "Deactivate rule" [ref=e183] [cursor=pointer]
              - row "Allen Heritage Gas Safe xlsx xlsx-master-helper-1.7 £120.00 £151.20 £302.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e184]:
                - cell "Allen Heritage" [ref=e185]
                - cell "Gas Safe" [ref=e186]
                - cell "xlsx" [ref=e187]
                - cell "xlsx-master-helper-1.7" [ref=e188]:
                  - link "xlsx-master-helper-1.7" [ref=e189] [cursor=pointer]:
                    - /url: /rules/daebbf38-76a8-4a80-b632-70919b234992
                - cell "£120.00" [ref=e190]
                - cell "£151.20" [ref=e191]
                - cell "£302.40" [ref=e192]
                - cell "20%" [ref=e193]
                - cell "20%" [ref=e194]
                - cell "2024-01-01" [ref=e195]
                - cell "—" [ref=e196]
                - cell "Active" [ref=e197]
                - cell "View rule Edit rule Deactivate rule" [ref=e198]:
                  - generic [ref=e199]:
                    - link "View rule" [ref=e200] [cursor=pointer]:
                      - /url: /rules/daebbf38-76a8-4a80-b632-70919b234992
                    - link "Edit rule" [ref=e201] [cursor=pointer]:
                      - /url: /rules/daebbf38-76a8-4a80-b632-70919b234992?edit=1
                    - button "Deactivate rule" [ref=e202] [cursor=pointer]
              - row "Allen Heritage Leak Investigation xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e203]:
                - cell "Allen Heritage" [ref=e204]
                - cell "Leak Investigation" [ref=e205]
                - cell "xlsx" [ref=e206]
                - cell "xlsx-master-helper-1.7" [ref=e207]:
                  - link "xlsx-master-helper-1.7" [ref=e208] [cursor=pointer]:
                    - /url: /rules/698dd6fb-aa0d-4d34-a2f2-4d1f317ba01c
                - cell "£150.00" [ref=e209]
                - cell "£189.00" [ref=e210]
                - cell "£378.00" [ref=e211]
                - cell "20%" [ref=e212]
                - cell "20%" [ref=e213]
                - cell "2024-01-01" [ref=e214]
                - cell "—" [ref=e215]
                - cell "Active" [ref=e216]
                - cell "View rule Edit rule Deactivate rule" [ref=e217]:
                  - generic [ref=e218]:
                    - link "View rule" [ref=e219] [cursor=pointer]:
                      - /url: /rules/698dd6fb-aa0d-4d34-a2f2-4d1f317ba01c
                    - link "Edit rule" [ref=e220] [cursor=pointer]:
                      - /url: /rules/698dd6fb-aa0d-4d34-a2f2-4d1f317ba01c?edit=1
                    - button "Deactivate rule" [ref=e221] [cursor=pointer]
              - row "Allen Heritage Multi-trader xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e222]:
                - cell "Allen Heritage" [ref=e223]
                - cell "Multi-trader" [ref=e224]
                - cell "xlsx" [ref=e225]
                - cell "xlsx-master-helper-1.7" [ref=e226]:
                  - link "xlsx-master-helper-1.7" [ref=e227] [cursor=pointer]:
                    - /url: /rules/88237a90-e8a2-4107-961a-2eacebb57191
                - cell "£95.00" [ref=e228]
                - cell "£119.70" [ref=e229]
                - cell "£239.40" [ref=e230]
                - cell "20%" [ref=e231]
                - cell "20%" [ref=e232]
                - cell "2024-01-01" [ref=e233]
                - cell "—" [ref=e234]
                - cell "Active" [ref=e235]
                - cell "View rule Edit rule Deactivate rule" [ref=e236]:
                  - generic [ref=e237]:
                    - link "View rule" [ref=e238] [cursor=pointer]:
                      - /url: /rules/88237a90-e8a2-4107-961a-2eacebb57191
                    - link "Edit rule" [ref=e239] [cursor=pointer]:
                      - /url: /rules/88237a90-e8a2-4107-961a-2eacebb57191?edit=1
                    - button "Deactivate rule" [ref=e240] [cursor=pointer]
              - row "Allen Heritage Painter & Decorator xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e241]:
                - cell "Allen Heritage" [ref=e242]
                - cell "Painter & Decorator" [ref=e243]
                - cell "xlsx" [ref=e244]
                - cell "xlsx-master-helper-1.7" [ref=e245]:
                  - link "xlsx-master-helper-1.7" [ref=e246] [cursor=pointer]:
                    - /url: /rules/f360ce1a-7491-4cc2-a02d-f531162f22e7
                - cell "£95.00" [ref=e247]
                - cell "£119.70" [ref=e248]
                - cell "£239.40" [ref=e249]
                - cell "20%" [ref=e250]
                - cell "20%" [ref=e251]
                - cell "2024-01-01" [ref=e252]
                - cell "—" [ref=e253]
                - cell "Active" [ref=e254]
                - cell "View rule Edit rule Deactivate rule" [ref=e255]:
                  - generic [ref=e256]:
                    - link "View rule" [ref=e257] [cursor=pointer]:
                      - /url: /rules/f360ce1a-7491-4cc2-a02d-f531162f22e7
                    - link "Edit rule" [ref=e258] [cursor=pointer]:
                      - /url: /rules/f360ce1a-7491-4cc2-a02d-f531162f22e7?edit=1
                    - button "Deactivate rule" [ref=e259] [cursor=pointer]
              - row "Allen Heritage Paths & Patios xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e260]:
                - cell "Allen Heritage" [ref=e261]
                - cell "Paths & Patios" [ref=e262]
                - cell "xlsx" [ref=e263]
                - cell "xlsx-master-helper-1.7" [ref=e264]:
                  - link "xlsx-master-helper-1.7" [ref=e265] [cursor=pointer]:
                    - /url: /rules/111510d4-e84f-4eeb-99ed-bc3524ff9b84
                - cell "£95.00" [ref=e266]
                - cell "£119.70" [ref=e267]
                - cell "£239.40" [ref=e268]
                - cell "20%" [ref=e269]
                - cell "20%" [ref=e270]
                - cell "2024-01-01" [ref=e271]
                - cell "—" [ref=e272]
                - cell "Active" [ref=e273]
                - cell "View rule Edit rule Deactivate rule" [ref=e274]:
                  - generic [ref=e275]:
                    - link "View rule" [ref=e276] [cursor=pointer]:
                      - /url: /rules/111510d4-e84f-4eeb-99ed-bc3524ff9b84
                    - link "Edit rule" [ref=e277] [cursor=pointer]:
                      - /url: /rules/111510d4-e84f-4eeb-99ed-bc3524ff9b84?edit=1
                    - button "Deactivate rule" [ref=e278] [cursor=pointer]
              - row "Allen Heritage Plasterer & Tiller xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e279]:
                - cell "Allen Heritage" [ref=e280]
                - cell "Plasterer & Tiller" [ref=e281]
                - cell "xlsx" [ref=e282]
                - cell "xlsx-master-helper-1.7" [ref=e283]:
                  - link "xlsx-master-helper-1.7" [ref=e284] [cursor=pointer]:
                    - /url: /rules/f21fdeae-e6c8-4d75-b35b-63b1704ebc65
                - cell "£95.00" [ref=e285]
                - cell "£119.70" [ref=e286]
                - cell "£239.40" [ref=e287]
                - cell "20%" [ref=e288]
                - cell "20%" [ref=e289]
                - cell "2024-01-01" [ref=e290]
                - cell "—" [ref=e291]
                - cell "Active" [ref=e292]
                - cell "View rule Edit rule Deactivate rule" [ref=e293]:
                  - generic [ref=e294]:
                    - link "View rule" [ref=e295] [cursor=pointer]:
                      - /url: /rules/f21fdeae-e6c8-4d75-b35b-63b1704ebc65
                    - link "Edit rule" [ref=e296] [cursor=pointer]:
                      - /url: /rules/f21fdeae-e6c8-4d75-b35b-63b1704ebc65?edit=1
                    - button "Deactivate rule" [ref=e297] [cursor=pointer]
              - row "Allen Heritage Plumber xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e298]:
                - cell "Allen Heritage" [ref=e299]
                - cell "Plumber" [ref=e300]
                - cell "xlsx" [ref=e301]
                - cell "xlsx-master-helper-1.7" [ref=e302]:
                  - link "xlsx-master-helper-1.7" [ref=e303] [cursor=pointer]:
                    - /url: /rules/fa62e260-1eb5-4130-9c27-aaf9266ae6af
                - cell "£95.00" [ref=e304]
                - cell "£119.70" [ref=e305]
                - cell "£239.40" [ref=e306]
                - cell "20%" [ref=e307]
                - cell "20%" [ref=e308]
                - cell "2024-01-01" [ref=e309]
                - cell "—" [ref=e310]
                - cell "Active" [ref=e311]
                - cell "View rule Edit rule Deactivate rule" [ref=e312]:
                  - generic [ref=e313]:
                    - link "View rule" [ref=e314] [cursor=pointer]:
                      - /url: /rules/fa62e260-1eb5-4130-9c27-aaf9266ae6af
                    - link "Edit rule" [ref=e315] [cursor=pointer]:
                      - /url: /rules/fa62e260-1eb5-4130-9c27-aaf9266ae6af?edit=1
                    - button "Deactivate rule" [ref=e316] [cursor=pointer]
              - row "Allen Heritage Roof Investigation xlsx xlsx-master-helper-1.7 £190.00 £239.40 £478.80 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e317]:
                - cell "Allen Heritage" [ref=e318]
                - cell "Roof Investigation" [ref=e319]
                - cell "xlsx" [ref=e320]
                - cell "xlsx-master-helper-1.7" [ref=e321]:
                  - link "xlsx-master-helper-1.7" [ref=e322] [cursor=pointer]:
                    - /url: /rules/e84d0147-cf2a-4021-9a94-6fbd63b28aa1
                - cell "£190.00" [ref=e323]
                - cell "£239.40" [ref=e324]
                - cell "£478.80" [ref=e325]
                - cell "20%" [ref=e326]
                - cell "20%" [ref=e327]
                - cell "2024-01-01" [ref=e328]
                - cell "—" [ref=e329]
                - cell "Active" [ref=e330]
                - cell "View rule Edit rule Deactivate rule" [ref=e331]:
                  - generic [ref=e332]:
                    - link "View rule" [ref=e333] [cursor=pointer]:
                      - /url: /rules/e84d0147-cf2a-4021-9a94-6fbd63b28aa1
                    - link "Edit rule" [ref=e334] [cursor=pointer]:
                      - /url: /rules/e84d0147-cf2a-4021-9a94-6fbd63b28aa1?edit=1
                    - button "Deactivate rule" [ref=e335] [cursor=pointer]
              - row "Allen Heritage Roofer xlsx xlsx-master-helper-1.7 £100.00 £126.00 £252.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e336]:
                - cell "Allen Heritage" [ref=e337]
                - cell "Roofer" [ref=e338]
                - cell "xlsx" [ref=e339]
                - cell "xlsx-master-helper-1.7" [ref=e340]:
                  - link "xlsx-master-helper-1.7" [ref=e341] [cursor=pointer]:
                    - /url: /rules/f3b5485e-4a7c-45df-aa1b-17d1b7035d7e
                - cell "£100.00" [ref=e342]
                - cell "£126.00" [ref=e343]
                - cell "£252.00" [ref=e344]
                - cell "20%" [ref=e345]
                - cell "20%" [ref=e346]
                - cell "2024-01-01" [ref=e347]
                - cell "—" [ref=e348]
                - cell "Active" [ref=e349]
                - cell "View rule Edit rule Deactivate rule" [ref=e350]:
                  - generic [ref=e351]:
                    - link "View rule" [ref=e352] [cursor=pointer]:
                      - /url: /rules/f3b5485e-4a7c-45df-aa1b-17d1b7035d7e
                    - link "Edit rule" [ref=e353] [cursor=pointer]:
                      - /url: /rules/f3b5485e-4a7c-45df-aa1b-17d1b7035d7e?edit=1
                    - button "Deactivate rule" [ref=e354] [cursor=pointer]
              - row "Apna Ghar Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e355]:
                - cell "Apna Ghar" [ref=e356]
                - cell "Carpenter" [ref=e357]
                - cell "xlsx" [ref=e358]
                - cell "xlsx-master-helper-1.7" [ref=e359]:
                  - link "xlsx-master-helper-1.7" [ref=e360] [cursor=pointer]:
                    - /url: /rules/2c260df2-f3cb-4d15-bab7-ac23c71404f9
                - cell "£95.00" [ref=e361]
                - cell "£119.70" [ref=e362]
                - cell "£239.40" [ref=e363]
                - cell "20%" [ref=e364]
                - cell "20%" [ref=e365]
                - cell "2024-01-01" [ref=e366]
                - cell "—" [ref=e367]
                - cell "Active" [ref=e368]
                - cell "View rule Edit rule Deactivate rule" [ref=e369]:
                  - generic [ref=e370]:
                    - link "View rule" [ref=e371] [cursor=pointer]:
                      - /url: /rules/2c260df2-f3cb-4d15-bab7-ac23c71404f9
                    - link "Edit rule" [ref=e372] [cursor=pointer]:
                      - /url: /rules/2c260df2-f3cb-4d15-bab7-ac23c71404f9?edit=1
                    - button "Deactivate rule" [ref=e373] [cursor=pointer]
              - row "Apna Ghar Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e374]:
                - cell "Apna Ghar" [ref=e375]
                - cell "Doors, Windows & Locks" [ref=e376]
                - cell "xlsx" [ref=e377]
                - cell "xlsx-master-helper-1.7" [ref=e378]:
                  - link "xlsx-master-helper-1.7" [ref=e379] [cursor=pointer]:
                    - /url: /rules/40fe058f-cee3-4a31-8683-45909d29bf85
                - cell "£95.00" [ref=e380]
                - cell "£119.70" [ref=e381]
                - cell "£239.40" [ref=e382]
                - cell "20%" [ref=e383]
                - cell "20%" [ref=e384]
                - cell "2024-01-01" [ref=e385]
                - cell "—" [ref=e386]
                - cell "Active" [ref=e387]
                - cell "View rule Edit rule Deactivate rule" [ref=e388]:
                  - generic [ref=e389]:
                    - link "View rule" [ref=e390] [cursor=pointer]:
                      - /url: /rules/40fe058f-cee3-4a31-8683-45909d29bf85
                    - link "Edit rule" [ref=e391] [cursor=pointer]:
                      - /url: /rules/40fe058f-cee3-4a31-8683-45909d29bf85?edit=1
                    - button "Deactivate rule" [ref=e392] [cursor=pointer]
              - row "Apna Ghar Drains & Blockages xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e393]:
                - cell "Apna Ghar" [ref=e394]
                - cell "Drains & Blockages" [ref=e395]
                - cell "xlsx" [ref=e396]
                - cell "xlsx-master-helper-1.7" [ref=e397]:
                  - link "xlsx-master-helper-1.7" [ref=e398] [cursor=pointer]:
                    - /url: /rules/a05984a6-8fcb-45b0-9253-36295c114bdb
                - cell "£150.00" [ref=e399]
                - cell "£189.00" [ref=e400]
                - cell "£378.00" [ref=e401]
                - cell "20%" [ref=e402]
                - cell "20%" [ref=e403]
                - cell "2024-01-01" [ref=e404]
                - cell "—" [ref=e405]
                - cell "Active" [ref=e406]
                - cell "View rule Edit rule Deactivate rule" [ref=e407]:
                  - generic [ref=e408]:
                    - link "View rule" [ref=e409] [cursor=pointer]:
                      - /url: /rules/a05984a6-8fcb-45b0-9253-36295c114bdb
                    - link "Edit rule" [ref=e410] [cursor=pointer]:
                      - /url: /rules/a05984a6-8fcb-45b0-9253-36295c114bdb?edit=1
                    - button "Deactivate rule" [ref=e411] [cursor=pointer]
              - row "Apna Ghar Electrician xlsx xlsx-master-helper-1.7 £110.00 £138.60 £277.20 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e412]:
                - cell "Apna Ghar" [ref=e413]
                - cell "Electrician" [ref=e414]
                - cell "xlsx" [ref=e415]
                - cell "xlsx-master-helper-1.7" [ref=e416]:
                  - link "xlsx-master-helper-1.7" [ref=e417] [cursor=pointer]:
                    - /url: /rules/c5ff6681-bd84-4f62-b1c4-464a2d80c8d7
                - cell "£110.00" [ref=e418]
                - cell "£138.60" [ref=e419]
                - cell "£277.20" [ref=e420]
                - cell "20%" [ref=e421]
                - cell "20%" [ref=e422]
                - cell "2024-01-01" [ref=e423]
                - cell "—" [ref=e424]
                - cell "Active" [ref=e425]
                - cell "View rule Edit rule Deactivate rule" [ref=e426]:
                  - generic [ref=e427]:
                    - link "View rule" [ref=e428] [cursor=pointer]:
                      - /url: /rules/c5ff6681-bd84-4f62-b1c4-464a2d80c8d7
                    - link "Edit rule" [ref=e429] [cursor=pointer]:
                      - /url: /rules/c5ff6681-bd84-4f62-b1c4-464a2d80c8d7?edit=1
                    - button "Deactivate rule" [ref=e430] [cursor=pointer]
              - row "Apna Ghar Fencing & Decking xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e431]:
                - cell "Apna Ghar" [ref=e432]
                - cell "Fencing & Decking" [ref=e433]
                - cell "xlsx" [ref=e434]
                - cell "xlsx-master-helper-1.7" [ref=e435]:
                  - link "xlsx-master-helper-1.7" [ref=e436] [cursor=pointer]:
                    - /url: /rules/c849fcaf-2724-4721-8fab-9ab75716122a
                - cell "£95.00" [ref=e437]
                - cell "£119.70" [ref=e438]
                - cell "£239.40" [ref=e439]
                - cell "20%" [ref=e440]
                - cell "20%" [ref=e441]
                - cell "2024-01-01" [ref=e442]
                - cell "—" [ref=e443]
                - cell "Active" [ref=e444]
                - cell "View rule Edit rule Deactivate rule" [ref=e445]:
                  - generic [ref=e446]:
                    - link "View rule" [ref=e447] [cursor=pointer]:
                      - /url: /rules/c849fcaf-2724-4721-8fab-9ab75716122a
                    - link "Edit rule" [ref=e448] [cursor=pointer]:
                      - /url: /rules/c849fcaf-2724-4721-8fab-9ab75716122a?edit=1
                    - button "Deactivate rule" [ref=e449] [cursor=pointer]
              - row "Apna Ghar Fire Certificate xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e450]:
                - cell "Apna Ghar" [ref=e451]
                - cell "Fire Certificate" [ref=e452]
                - cell "xlsx" [ref=e453]
                - cell "xlsx-master-helper-1.7" [ref=e454]:
                  - link "xlsx-master-helper-1.7" [ref=e455] [cursor=pointer]:
                    - /url: /rules/753d3f5b-8c2c-43bc-ae3d-f06708c7c963
                - cell "£150.00" [ref=e456]
                - cell "£189.00" [ref=e457]
                - cell "£378.00" [ref=e458]
                - cell "20%" [ref=e459]
                - cell "20%" [ref=e460]
                - cell "2024-01-01" [ref=e461]
                - cell "—" [ref=e462]
                - cell "Active" [ref=e463]
                - cell "View rule Edit rule Deactivate rule" [ref=e464]:
                  - generic [ref=e465]:
                    - link "View rule" [ref=e466] [cursor=pointer]:
                      - /url: /rules/753d3f5b-8c2c-43bc-ae3d-f06708c7c963
                    - link "Edit rule" [ref=e467] [cursor=pointer]:
                      - /url: /rules/753d3f5b-8c2c-43bc-ae3d-f06708c7c963?edit=1
                    - button "Deactivate rule" [ref=e468] [cursor=pointer]
              - row "Apna Ghar Gardening xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e469]:
                - cell "Apna Ghar" [ref=e470]
                - cell "Gardening" [ref=e471]
                - cell "xlsx" [ref=e472]
                - cell "xlsx-master-helper-1.7" [ref=e473]:
                  - link "xlsx-master-helper-1.7" [ref=e474] [cursor=pointer]:
                    - /url: /rules/2d9a476a-f386-4e2f-bb5a-75d614b22cf7
                - cell "£95.00" [ref=e475]
                - cell "£119.70" [ref=e476]
                - cell "£239.40" [ref=e477]
                - cell "20%" [ref=e478]
                - cell "20%" [ref=e479]
                - cell "2024-01-01" [ref=e480]
                - cell "—" [ref=e481]
                - cell "Active" [ref=e482]
                - cell "View rule Edit rule Deactivate rule" [ref=e483]:
                  - generic [ref=e484]:
                    - link "View rule" [ref=e485] [cursor=pointer]:
                      - /url: /rules/2d9a476a-f386-4e2f-bb5a-75d614b22cf7
                    - link "Edit rule" [ref=e486] [cursor=pointer]:
                      - /url: /rules/2d9a476a-f386-4e2f-bb5a-75d614b22cf7?edit=1
                    - button "Deactivate rule" [ref=e487] [cursor=pointer]
              - row "Apna Ghar Gas Safe xlsx xlsx-master-helper-1.7 £120.00 £151.20 £302.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e488]:
                - cell "Apna Ghar" [ref=e489]
                - cell "Gas Safe" [ref=e490]
                - cell "xlsx" [ref=e491]
                - cell "xlsx-master-helper-1.7" [ref=e492]:
                  - link "xlsx-master-helper-1.7" [ref=e493] [cursor=pointer]:
                    - /url: /rules/969c694c-41e0-4748-b46c-63374ddb1afd
                - cell "£120.00" [ref=e494]
                - cell "£151.20" [ref=e495]
                - cell "£302.40" [ref=e496]
                - cell "20%" [ref=e497]
                - cell "20%" [ref=e498]
                - cell "2024-01-01" [ref=e499]
                - cell "—" [ref=e500]
                - cell "Active" [ref=e501]
                - cell "View rule Edit rule Deactivate rule" [ref=e502]:
                  - generic [ref=e503]:
                    - link "View rule" [ref=e504] [cursor=pointer]:
                      - /url: /rules/969c694c-41e0-4748-b46c-63374ddb1afd
                    - link "Edit rule" [ref=e505] [cursor=pointer]:
                      - /url: /rules/969c694c-41e0-4748-b46c-63374ddb1afd?edit=1
                    - button "Deactivate rule" [ref=e506] [cursor=pointer]
              - row "Apna Ghar Leak Investigation xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e507]:
                - cell "Apna Ghar" [ref=e508]
                - cell "Leak Investigation" [ref=e509]
                - cell "xlsx" [ref=e510]
                - cell "xlsx-master-helper-1.7" [ref=e511]:
                  - link "xlsx-master-helper-1.7" [ref=e512] [cursor=pointer]:
                    - /url: /rules/694e03dc-adb2-4c7d-a4e0-f2f3d0be1119
                - cell "£150.00" [ref=e513]
                - cell "£189.00" [ref=e514]
                - cell "£378.00" [ref=e515]
                - cell "20%" [ref=e516]
                - cell "20%" [ref=e517]
                - cell "2024-01-01" [ref=e518]
                - cell "—" [ref=e519]
                - cell "Active" [ref=e520]
                - cell "View rule Edit rule Deactivate rule" [ref=e521]:
                  - generic [ref=e522]:
                    - link "View rule" [ref=e523] [cursor=pointer]:
                      - /url: /rules/694e03dc-adb2-4c7d-a4e0-f2f3d0be1119
                    - link "Edit rule" [ref=e524] [cursor=pointer]:
                      - /url: /rules/694e03dc-adb2-4c7d-a4e0-f2f3d0be1119?edit=1
                    - button "Deactivate rule" [ref=e525] [cursor=pointer]
              - row "Apna Ghar Multi-trader xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e526]:
                - cell "Apna Ghar" [ref=e527]
                - cell "Multi-trader" [ref=e528]
                - cell "xlsx" [ref=e529]
                - cell "xlsx-master-helper-1.7" [ref=e530]:
                  - link "xlsx-master-helper-1.7" [ref=e531] [cursor=pointer]:
                    - /url: /rules/c6c81f2c-1912-40de-b70d-88886e8bdf54
                - cell "£95.00" [ref=e532]
                - cell "£119.70" [ref=e533]
                - cell "£239.40" [ref=e534]
                - cell "20%" [ref=e535]
                - cell "20%" [ref=e536]
                - cell "2024-01-01" [ref=e537]
                - cell "—" [ref=e538]
                - cell "Active" [ref=e539]
                - cell "View rule Edit rule Deactivate rule" [ref=e540]:
                  - generic [ref=e541]:
                    - link "View rule" [ref=e542] [cursor=pointer]:
                      - /url: /rules/c6c81f2c-1912-40de-b70d-88886e8bdf54
                    - link "Edit rule" [ref=e543] [cursor=pointer]:
                      - /url: /rules/c6c81f2c-1912-40de-b70d-88886e8bdf54?edit=1
                    - button "Deactivate rule" [ref=e544] [cursor=pointer]
              - row "Apna Ghar Painter & Decorator xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e545]:
                - cell "Apna Ghar" [ref=e546]
                - cell "Painter & Decorator" [ref=e547]
                - cell "xlsx" [ref=e548]
                - cell "xlsx-master-helper-1.7" [ref=e549]:
                  - link "xlsx-master-helper-1.7" [ref=e550] [cursor=pointer]:
                    - /url: /rules/ea230736-c7da-45c1-9599-16b068451e38
                - cell "£95.00" [ref=e551]
                - cell "£119.70" [ref=e552]
                - cell "£239.40" [ref=e553]
                - cell "20%" [ref=e554]
                - cell "20%" [ref=e555]
                - cell "2024-01-01" [ref=e556]
                - cell "—" [ref=e557]
                - cell "Active" [ref=e558]
                - cell "View rule Edit rule Deactivate rule" [ref=e559]:
                  - generic [ref=e560]:
                    - link "View rule" [ref=e561] [cursor=pointer]:
                      - /url: /rules/ea230736-c7da-45c1-9599-16b068451e38
                    - link "Edit rule" [ref=e562] [cursor=pointer]:
                      - /url: /rules/ea230736-c7da-45c1-9599-16b068451e38?edit=1
                    - button "Deactivate rule" [ref=e563] [cursor=pointer]
              - row "Apna Ghar Paths & Patios xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e564]:
                - cell "Apna Ghar" [ref=e565]
                - cell "Paths & Patios" [ref=e566]
                - cell "xlsx" [ref=e567]
                - cell "xlsx-master-helper-1.7" [ref=e568]:
                  - link "xlsx-master-helper-1.7" [ref=e569] [cursor=pointer]:
                    - /url: /rules/12b4127a-0681-41b8-958e-b2b58aeb447d
                - cell "£95.00" [ref=e570]
                - cell "£119.70" [ref=e571]
                - cell "£239.40" [ref=e572]
                - cell "20%" [ref=e573]
                - cell "20%" [ref=e574]
                - cell "2024-01-01" [ref=e575]
                - cell "—" [ref=e576]
                - cell "Active" [ref=e577]
                - cell "View rule Edit rule Deactivate rule" [ref=e578]:
                  - generic [ref=e579]:
                    - link "View rule" [ref=e580] [cursor=pointer]:
                      - /url: /rules/12b4127a-0681-41b8-958e-b2b58aeb447d
                    - link "Edit rule" [ref=e581] [cursor=pointer]:
                      - /url: /rules/12b4127a-0681-41b8-958e-b2b58aeb447d?edit=1
                    - button "Deactivate rule" [ref=e582] [cursor=pointer]
              - row "Apna Ghar Plasterer & Tiller xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e583]:
                - cell "Apna Ghar" [ref=e584]
                - cell "Plasterer & Tiller" [ref=e585]
                - cell "xlsx" [ref=e586]
                - cell "xlsx-master-helper-1.7" [ref=e587]:
                  - link "xlsx-master-helper-1.7" [ref=e588] [cursor=pointer]:
                    - /url: /rules/36fcb834-1d3e-4f52-917c-6bb6415b9c03
                - cell "£95.00" [ref=e589]
                - cell "£119.70" [ref=e590]
                - cell "£239.40" [ref=e591]
                - cell "20%" [ref=e592]
                - cell "20%" [ref=e593]
                - cell "2024-01-01" [ref=e594]
                - cell "—" [ref=e595]
                - cell "Active" [ref=e596]
                - cell "View rule Edit rule Deactivate rule" [ref=e597]:
                  - generic [ref=e598]:
                    - link "View rule" [ref=e599] [cursor=pointer]:
                      - /url: /rules/36fcb834-1d3e-4f52-917c-6bb6415b9c03
                    - link "Edit rule" [ref=e600] [cursor=pointer]:
                      - /url: /rules/36fcb834-1d3e-4f52-917c-6bb6415b9c03?edit=1
                    - button "Deactivate rule" [ref=e601] [cursor=pointer]
              - row "Apna Ghar Plumber xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e602]:
                - cell "Apna Ghar" [ref=e603]
                - cell "Plumber" [ref=e604]
                - cell "xlsx" [ref=e605]
                - cell "xlsx-master-helper-1.7" [ref=e606]:
                  - link "xlsx-master-helper-1.7" [ref=e607] [cursor=pointer]:
                    - /url: /rules/a06467ae-f5e9-4d8c-bce2-2cc497f49cfc
                - cell "£95.00" [ref=e608]
                - cell "£119.70" [ref=e609]
                - cell "£239.40" [ref=e610]
                - cell "20%" [ref=e611]
                - cell "20%" [ref=e612]
                - cell "2024-01-01" [ref=e613]
                - cell "—" [ref=e614]
                - cell "Active" [ref=e615]
                - cell "View rule Edit rule Deactivate rule" [ref=e616]:
                  - generic [ref=e617]:
                    - link "View rule" [ref=e618] [cursor=pointer]:
                      - /url: /rules/a06467ae-f5e9-4d8c-bce2-2cc497f49cfc
                    - link "Edit rule" [ref=e619] [cursor=pointer]:
                      - /url: /rules/a06467ae-f5e9-4d8c-bce2-2cc497f49cfc?edit=1
                    - button "Deactivate rule" [ref=e620] [cursor=pointer]
              - row "Apna Ghar Roof Investigation xlsx xlsx-master-helper-1.7 £190.00 £239.40 £478.80 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e621]:
                - cell "Apna Ghar" [ref=e622]
                - cell "Roof Investigation" [ref=e623]
                - cell "xlsx" [ref=e624]
                - cell "xlsx-master-helper-1.7" [ref=e625]:
                  - link "xlsx-master-helper-1.7" [ref=e626] [cursor=pointer]:
                    - /url: /rules/0412e219-043a-4d37-9915-f4226d280d75
                - cell "£190.00" [ref=e627]
                - cell "£239.40" [ref=e628]
                - cell "£478.80" [ref=e629]
                - cell "20%" [ref=e630]
                - cell "20%" [ref=e631]
                - cell "2024-01-01" [ref=e632]
                - cell "—" [ref=e633]
                - cell "Active" [ref=e634]
                - cell "View rule Edit rule Deactivate rule" [ref=e635]:
                  - generic [ref=e636]:
                    - link "View rule" [ref=e637] [cursor=pointer]:
                      - /url: /rules/0412e219-043a-4d37-9915-f4226d280d75
                    - link "Edit rule" [ref=e638] [cursor=pointer]:
                      - /url: /rules/0412e219-043a-4d37-9915-f4226d280d75?edit=1
                    - button "Deactivate rule" [ref=e639] [cursor=pointer]
              - row "Apna Ghar Roofer xlsx xlsx-master-helper-1.7 £100.00 £126.00 £252.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e640]:
                - cell "Apna Ghar" [ref=e641]
                - cell "Roofer" [ref=e642]
                - cell "xlsx" [ref=e643]
                - cell "xlsx-master-helper-1.7" [ref=e644]:
                  - link "xlsx-master-helper-1.7" [ref=e645] [cursor=pointer]:
                    - /url: /rules/7d202687-4eb3-4f8b-ac48-aaee2389ed49
                - cell "£100.00" [ref=e646]
                - cell "£126.00" [ref=e647]
                - cell "£252.00" [ref=e648]
                - cell "20%" [ref=e649]
                - cell "20%" [ref=e650]
                - cell "2024-01-01" [ref=e651]
                - cell "—" [ref=e652]
                - cell "Active" [ref=e653]
                - cell "View rule Edit rule Deactivate rule" [ref=e654]:
                  - generic [ref=e655]:
                    - link "View rule" [ref=e656] [cursor=pointer]:
                      - /url: /rules/7d202687-4eb3-4f8b-ac48-aaee2389ed49
                    - link "Edit rule" [ref=e657] [cursor=pointer]:
                      - /url: /rules/7d202687-4eb3-4f8b-ac48-aaee2389ed49?edit=1
                    - button "Deactivate rule" [ref=e658] [cursor=pointer]
              - row "Apnar Ghar Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e659]:
                - cell "Apnar Ghar" [ref=e660]
                - cell "Carpenter" [ref=e661]
                - cell "xlsx" [ref=e662]
                - cell "xlsx-master-helper-1.7" [ref=e663]:
                  - link "xlsx-master-helper-1.7" [ref=e664] [cursor=pointer]:
                    - /url: /rules/5c371089-ef73-4476-a2ef-a52ceea3dd50
                - cell "£95.00" [ref=e665]
                - cell "£119.70" [ref=e666]
                - cell "£239.40" [ref=e667]
                - cell "20%" [ref=e668]
                - cell "20%" [ref=e669]
                - cell "2024-01-01" [ref=e670]
                - cell "—" [ref=e671]
                - cell "Active" [ref=e672]
                - cell "View rule Edit rule Deactivate rule" [ref=e673]:
                  - generic [ref=e674]:
                    - link "View rule" [ref=e675] [cursor=pointer]:
                      - /url: /rules/5c371089-ef73-4476-a2ef-a52ceea3dd50
                    - link "Edit rule" [ref=e676] [cursor=pointer]:
                      - /url: /rules/5c371089-ef73-4476-a2ef-a52ceea3dd50?edit=1
                    - button "Deactivate rule" [ref=e677] [cursor=pointer]
              - row "Apnar Ghar Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e678]:
                - cell "Apnar Ghar" [ref=e679]
                - cell "Doors, Windows & Locks" [ref=e680]
                - cell "xlsx" [ref=e681]
                - cell "xlsx-master-helper-1.7" [ref=e682]:
                  - link "xlsx-master-helper-1.7" [ref=e683] [cursor=pointer]:
                    - /url: /rules/85b3fc76-172c-4b48-ab2d-a2510884771a
                - cell "£95.00" [ref=e684]
                - cell "£119.70" [ref=e685]
                - cell "£239.40" [ref=e686]
                - cell "20%" [ref=e687]
                - cell "20%" [ref=e688]
                - cell "2024-01-01" [ref=e689]
                - cell "—" [ref=e690]
                - cell "Active" [ref=e691]
                - cell "View rule Edit rule Deactivate rule" [ref=e692]:
                  - generic [ref=e693]:
                    - link "View rule" [ref=e694] [cursor=pointer]:
                      - /url: /rules/85b3fc76-172c-4b48-ab2d-a2510884771a
                    - link "Edit rule" [ref=e695] [cursor=pointer]:
                      - /url: /rules/85b3fc76-172c-4b48-ab2d-a2510884771a?edit=1
                    - button "Deactivate rule" [ref=e696] [cursor=pointer]
              - row "Apnar Ghar Drains & Blockages xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e697]:
                - cell "Apnar Ghar" [ref=e698]
                - cell "Drains & Blockages" [ref=e699]
                - cell "xlsx" [ref=e700]
                - cell "xlsx-master-helper-1.7" [ref=e701]:
                  - link "xlsx-master-helper-1.7" [ref=e702] [cursor=pointer]:
                    - /url: /rules/6e8b9e47-bff6-4dc0-ae2c-7f86d60c9907
                - cell "£150.00" [ref=e703]
                - cell "£189.00" [ref=e704]
                - cell "£378.00" [ref=e705]
                - cell "20%" [ref=e706]
                - cell "20%" [ref=e707]
                - cell "2024-01-01" [ref=e708]
                - cell "—" [ref=e709]
                - cell "Active" [ref=e710]
                - cell "View rule Edit rule Deactivate rule" [ref=e711]:
                  - generic [ref=e712]:
                    - link "View rule" [ref=e713] [cursor=pointer]:
                      - /url: /rules/6e8b9e47-bff6-4dc0-ae2c-7f86d60c9907
                    - link "Edit rule" [ref=e714] [cursor=pointer]:
                      - /url: /rules/6e8b9e47-bff6-4dc0-ae2c-7f86d60c9907?edit=1
                    - button "Deactivate rule" [ref=e715] [cursor=pointer]
              - row "Apnar Ghar Electrician xlsx xlsx-master-helper-1.7 £110.00 £138.60 £277.20 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e716]:
                - cell "Apnar Ghar" [ref=e717]
                - cell "Electrician" [ref=e718]
                - cell "xlsx" [ref=e719]
                - cell "xlsx-master-helper-1.7" [ref=e720]:
                  - link "xlsx-master-helper-1.7" [ref=e721] [cursor=pointer]:
                    - /url: /rules/f644593f-507a-4b6f-99b4-4e8736c20083
                - cell "£110.00" [ref=e722]
                - cell "£138.60" [ref=e723]
                - cell "£277.20" [ref=e724]
                - cell "20%" [ref=e725]
                - cell "20%" [ref=e726]
                - cell "2024-01-01" [ref=e727]
                - cell "—" [ref=e728]
                - cell "Active" [ref=e729]
                - cell "View rule Edit rule Deactivate rule" [ref=e730]:
                  - generic [ref=e731]:
                    - link "View rule" [ref=e732] [cursor=pointer]:
                      - /url: /rules/f644593f-507a-4b6f-99b4-4e8736c20083
                    - link "Edit rule" [ref=e733] [cursor=pointer]:
                      - /url: /rules/f644593f-507a-4b6f-99b4-4e8736c20083?edit=1
                    - button "Deactivate rule" [ref=e734] [cursor=pointer]
              - row "Apnar Ghar Fencing & Decking xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e735]:
                - cell "Apnar Ghar" [ref=e736]
                - cell "Fencing & Decking" [ref=e737]
                - cell "xlsx" [ref=e738]
                - cell "xlsx-master-helper-1.7" [ref=e739]:
                  - link "xlsx-master-helper-1.7" [ref=e740] [cursor=pointer]:
                    - /url: /rules/5e84687d-191e-4a44-a885-c176ea63d79e
                - cell "£95.00" [ref=e741]
                - cell "£119.70" [ref=e742]
                - cell "£239.40" [ref=e743]
                - cell "20%" [ref=e744]
                - cell "20%" [ref=e745]
                - cell "2024-01-01" [ref=e746]
                - cell "—" [ref=e747]
                - cell "Active" [ref=e748]
                - cell "View rule Edit rule Deactivate rule" [ref=e749]:
                  - generic [ref=e750]:
                    - link "View rule" [ref=e751] [cursor=pointer]:
                      - /url: /rules/5e84687d-191e-4a44-a885-c176ea63d79e
                    - link "Edit rule" [ref=e752] [cursor=pointer]:
                      - /url: /rules/5e84687d-191e-4a44-a885-c176ea63d79e?edit=1
                    - button "Deactivate rule" [ref=e753] [cursor=pointer]
              - row "Apnar Ghar Fire Certificate xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e754]:
                - cell "Apnar Ghar" [ref=e755]
                - cell "Fire Certificate" [ref=e756]
                - cell "xlsx" [ref=e757]
                - cell "xlsx-master-helper-1.7" [ref=e758]:
                  - link "xlsx-master-helper-1.7" [ref=e759] [cursor=pointer]:
                    - /url: /rules/96c8bf91-4d27-404a-9443-9dc53c58b214
                - cell "£150.00" [ref=e760]
                - cell "£189.00" [ref=e761]
                - cell "£378.00" [ref=e762]
                - cell "20%" [ref=e763]
                - cell "20%" [ref=e764]
                - cell "2024-01-01" [ref=e765]
                - cell "—" [ref=e766]
                - cell "Active" [ref=e767]
                - cell "View rule Edit rule Deactivate rule" [ref=e768]:
                  - generic [ref=e769]:
                    - link "View rule" [ref=e770] [cursor=pointer]:
                      - /url: /rules/96c8bf91-4d27-404a-9443-9dc53c58b214
                    - link "Edit rule" [ref=e771] [cursor=pointer]:
                      - /url: /rules/96c8bf91-4d27-404a-9443-9dc53c58b214?edit=1
                    - button "Deactivate rule" [ref=e772] [cursor=pointer]
              - row "Apnar Ghar Gardening xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e773]:
                - cell "Apnar Ghar" [ref=e774]
                - cell "Gardening" [ref=e775]
                - cell "xlsx" [ref=e776]
                - cell "xlsx-master-helper-1.7" [ref=e777]:
                  - link "xlsx-master-helper-1.7" [ref=e778] [cursor=pointer]:
                    - /url: /rules/5d737cbd-8d89-45e3-8190-3447795588a4
                - cell "£95.00" [ref=e779]
                - cell "£119.70" [ref=e780]
                - cell "£239.40" [ref=e781]
                - cell "20%" [ref=e782]
                - cell "20%" [ref=e783]
                - cell "2024-01-01" [ref=e784]
                - cell "—" [ref=e785]
                - cell "Active" [ref=e786]
                - cell "View rule Edit rule Deactivate rule" [ref=e787]:
                  - generic [ref=e788]:
                    - link "View rule" [ref=e789] [cursor=pointer]:
                      - /url: /rules/5d737cbd-8d89-45e3-8190-3447795588a4
                    - link "Edit rule" [ref=e790] [cursor=pointer]:
                      - /url: /rules/5d737cbd-8d89-45e3-8190-3447795588a4?edit=1
                    - button "Deactivate rule" [ref=e791] [cursor=pointer]
              - row "Apnar Ghar Gas Safe xlsx xlsx-master-helper-1.7 £120.00 £151.20 £302.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e792]:
                - cell "Apnar Ghar" [ref=e793]
                - cell "Gas Safe" [ref=e794]
                - cell "xlsx" [ref=e795]
                - cell "xlsx-master-helper-1.7" [ref=e796]:
                  - link "xlsx-master-helper-1.7" [ref=e797] [cursor=pointer]:
                    - /url: /rules/ca3382b6-7e14-4daf-82e6-d8f29450551b
                - cell "£120.00" [ref=e798]
                - cell "£151.20" [ref=e799]
                - cell "£302.40" [ref=e800]
                - cell "20%" [ref=e801]
                - cell "20%" [ref=e802]
                - cell "2024-01-01" [ref=e803]
                - cell "—" [ref=e804]
                - cell "Active" [ref=e805]
                - cell "View rule Edit rule Deactivate rule" [ref=e806]:
                  - generic [ref=e807]:
                    - link "View rule" [ref=e808] [cursor=pointer]:
                      - /url: /rules/ca3382b6-7e14-4daf-82e6-d8f29450551b
                    - link "Edit rule" [ref=e809] [cursor=pointer]:
                      - /url: /rules/ca3382b6-7e14-4daf-82e6-d8f29450551b?edit=1
                    - button "Deactivate rule" [ref=e810] [cursor=pointer]
              - row "Apnar Ghar Leak Investigation xlsx xlsx-master-helper-1.7 £150.00 £189.00 £378.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e811]:
                - cell "Apnar Ghar" [ref=e812]
                - cell "Leak Investigation" [ref=e813]
                - cell "xlsx" [ref=e814]
                - cell "xlsx-master-helper-1.7" [ref=e815]:
                  - link "xlsx-master-helper-1.7" [ref=e816] [cursor=pointer]:
                    - /url: /rules/7dba4ce8-cbc3-46ff-9271-728e0b182389
                - cell "£150.00" [ref=e817]
                - cell "£189.00" [ref=e818]
                - cell "£378.00" [ref=e819]
                - cell "20%" [ref=e820]
                - cell "20%" [ref=e821]
                - cell "2024-01-01" [ref=e822]
                - cell "—" [ref=e823]
                - cell "Active" [ref=e824]
                - cell "View rule Edit rule Deactivate rule" [ref=e825]:
                  - generic [ref=e826]:
                    - link "View rule" [ref=e827] [cursor=pointer]:
                      - /url: /rules/7dba4ce8-cbc3-46ff-9271-728e0b182389
                    - link "Edit rule" [ref=e828] [cursor=pointer]:
                      - /url: /rules/7dba4ce8-cbc3-46ff-9271-728e0b182389?edit=1
                    - button "Deactivate rule" [ref=e829] [cursor=pointer]
              - row "Apnar Ghar Multi-trader xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e830]:
                - cell "Apnar Ghar" [ref=e831]
                - cell "Multi-trader" [ref=e832]
                - cell "xlsx" [ref=e833]
                - cell "xlsx-master-helper-1.7" [ref=e834]:
                  - link "xlsx-master-helper-1.7" [ref=e835] [cursor=pointer]:
                    - /url: /rules/8771af7b-00c8-4e8d-aca2-ca7f3631cb95
                - cell "£95.00" [ref=e836]
                - cell "£119.70" [ref=e837]
                - cell "£239.40" [ref=e838]
                - cell "20%" [ref=e839]
                - cell "20%" [ref=e840]
                - cell "2024-01-01" [ref=e841]
                - cell "—" [ref=e842]
                - cell "Active" [ref=e843]
                - cell "View rule Edit rule Deactivate rule" [ref=e844]:
                  - generic [ref=e845]:
                    - link "View rule" [ref=e846] [cursor=pointer]:
                      - /url: /rules/8771af7b-00c8-4e8d-aca2-ca7f3631cb95
                    - link "Edit rule" [ref=e847] [cursor=pointer]:
                      - /url: /rules/8771af7b-00c8-4e8d-aca2-ca7f3631cb95?edit=1
                    - button "Deactivate rule" [ref=e848] [cursor=pointer]
              - row "Apnar Ghar Painter & Decorator xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e849]:
                - cell "Apnar Ghar" [ref=e850]
                - cell "Painter & Decorator" [ref=e851]
                - cell "xlsx" [ref=e852]
                - cell "xlsx-master-helper-1.7" [ref=e853]:
                  - link "xlsx-master-helper-1.7" [ref=e854] [cursor=pointer]:
                    - /url: /rules/cbf91783-63c2-43f3-ae98-b6ab7639f6cd
                - cell "£95.00" [ref=e855]
                - cell "£119.70" [ref=e856]
                - cell "£239.40" [ref=e857]
                - cell "20%" [ref=e858]
                - cell "20%" [ref=e859]
                - cell "2024-01-01" [ref=e860]
                - cell "—" [ref=e861]
                - cell "Active" [ref=e862]
                - cell "View rule Edit rule Deactivate rule" [ref=e863]:
                  - generic [ref=e864]:
                    - link "View rule" [ref=e865] [cursor=pointer]:
                      - /url: /rules/cbf91783-63c2-43f3-ae98-b6ab7639f6cd
                    - link "Edit rule" [ref=e866] [cursor=pointer]:
                      - /url: /rules/cbf91783-63c2-43f3-ae98-b6ab7639f6cd?edit=1
                    - button "Deactivate rule" [ref=e867] [cursor=pointer]
              - row "Apnar Ghar Paths & Patios xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e868]:
                - cell "Apnar Ghar" [ref=e869]
                - cell "Paths & Patios" [ref=e870]
                - cell "xlsx" [ref=e871]
                - cell "xlsx-master-helper-1.7" [ref=e872]:
                  - link "xlsx-master-helper-1.7" [ref=e873] [cursor=pointer]:
                    - /url: /rules/5b63681b-db34-4a04-bd68-00035f7c0d99
                - cell "£95.00" [ref=e874]
                - cell "£119.70" [ref=e875]
                - cell "£239.40" [ref=e876]
                - cell "20%" [ref=e877]
                - cell "20%" [ref=e878]
                - cell "2024-01-01" [ref=e879]
                - cell "—" [ref=e880]
                - cell "Active" [ref=e881]
                - cell "View rule Edit rule Deactivate rule" [ref=e882]:
                  - generic [ref=e883]:
                    - link "View rule" [ref=e884] [cursor=pointer]:
                      - /url: /rules/5b63681b-db34-4a04-bd68-00035f7c0d99
                    - link "Edit rule" [ref=e885] [cursor=pointer]:
                      - /url: /rules/5b63681b-db34-4a04-bd68-00035f7c0d99?edit=1
                    - button "Deactivate rule" [ref=e886] [cursor=pointer]
              - row "Apnar Ghar Plasterer & Tiller xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e887]:
                - cell "Apnar Ghar" [ref=e888]
                - cell "Plasterer & Tiller" [ref=e889]
                - cell "xlsx" [ref=e890]
                - cell "xlsx-master-helper-1.7" [ref=e891]:
                  - link "xlsx-master-helper-1.7" [ref=e892] [cursor=pointer]:
                    - /url: /rules/2ecce2f6-da21-4e5f-894f-28a1a6bea7b9
                - cell "£95.00" [ref=e893]
                - cell "£119.70" [ref=e894]
                - cell "£239.40" [ref=e895]
                - cell "20%" [ref=e896]
                - cell "20%" [ref=e897]
                - cell "2024-01-01" [ref=e898]
                - cell "—" [ref=e899]
                - cell "Active" [ref=e900]
                - cell "View rule Edit rule Deactivate rule" [ref=e901]:
                  - generic [ref=e902]:
                    - link "View rule" [ref=e903] [cursor=pointer]:
                      - /url: /rules/2ecce2f6-da21-4e5f-894f-28a1a6bea7b9
                    - link "Edit rule" [ref=e904] [cursor=pointer]:
                      - /url: /rules/2ecce2f6-da21-4e5f-894f-28a1a6bea7b9?edit=1
                    - button "Deactivate rule" [ref=e905] [cursor=pointer]
              - row "Apnar Ghar Plumber xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e906]:
                - cell "Apnar Ghar" [ref=e907]
                - cell "Plumber" [ref=e908]
                - cell "xlsx" [ref=e909]
                - cell "xlsx-master-helper-1.7" [ref=e910]:
                  - link "xlsx-master-helper-1.7" [ref=e911] [cursor=pointer]:
                    - /url: /rules/a3cf50cc-2463-43fa-b1e9-79b73e2b49fd
                - cell "£95.00" [ref=e912]
                - cell "£119.70" [ref=e913]
                - cell "£239.40" [ref=e914]
                - cell "20%" [ref=e915]
                - cell "20%" [ref=e916]
                - cell "2024-01-01" [ref=e917]
                - cell "—" [ref=e918]
                - cell "Active" [ref=e919]
                - cell "View rule Edit rule Deactivate rule" [ref=e920]:
                  - generic [ref=e921]:
                    - link "View rule" [ref=e922] [cursor=pointer]:
                      - /url: /rules/a3cf50cc-2463-43fa-b1e9-79b73e2b49fd
                    - link "Edit rule" [ref=e923] [cursor=pointer]:
                      - /url: /rules/a3cf50cc-2463-43fa-b1e9-79b73e2b49fd?edit=1
                    - button "Deactivate rule" [ref=e924] [cursor=pointer]
              - row "Apnar Ghar Roof Investigation xlsx xlsx-master-helper-1.7 £190.00 £239.40 £478.80 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e925]:
                - cell "Apnar Ghar" [ref=e926]
                - cell "Roof Investigation" [ref=e927]
                - cell "xlsx" [ref=e928]
                - cell "xlsx-master-helper-1.7" [ref=e929]:
                  - link "xlsx-master-helper-1.7" [ref=e930] [cursor=pointer]:
                    - /url: /rules/7bd78605-c07e-4289-86a0-0a97fd9655b2
                - cell "£190.00" [ref=e931]
                - cell "£239.40" [ref=e932]
                - cell "£478.80" [ref=e933]
                - cell "20%" [ref=e934]
                - cell "20%" [ref=e935]
                - cell "2024-01-01" [ref=e936]
                - cell "—" [ref=e937]
                - cell "Active" [ref=e938]
                - cell "View rule Edit rule Deactivate rule" [ref=e939]:
                  - generic [ref=e940]:
                    - link "View rule" [ref=e941] [cursor=pointer]:
                      - /url: /rules/7bd78605-c07e-4289-86a0-0a97fd9655b2
                    - link "Edit rule" [ref=e942] [cursor=pointer]:
                      - /url: /rules/7bd78605-c07e-4289-86a0-0a97fd9655b2?edit=1
                    - button "Deactivate rule" [ref=e943] [cursor=pointer]
              - row "Apnar Ghar Roofer xlsx xlsx-master-helper-1.7 £100.00 £126.00 £252.00 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e944]:
                - cell "Apnar Ghar" [ref=e945]
                - cell "Roofer" [ref=e946]
                - cell "xlsx" [ref=e947]
                - cell "xlsx-master-helper-1.7" [ref=e948]:
                  - link "xlsx-master-helper-1.7" [ref=e949] [cursor=pointer]:
                    - /url: /rules/ad40cf24-8b99-48b3-ba5f-24f4e28619f9
                - cell "£100.00" [ref=e950]
                - cell "£126.00" [ref=e951]
                - cell "£252.00" [ref=e952]
                - cell "20%" [ref=e953]
                - cell "20%" [ref=e954]
                - cell "2024-01-01" [ref=e955]
                - cell "—" [ref=e956]
                - cell "Active" [ref=e957]
                - cell "View rule Edit rule Deactivate rule" [ref=e958]:
                  - generic [ref=e959]:
                    - link "View rule" [ref=e960] [cursor=pointer]:
                      - /url: /rules/ad40cf24-8b99-48b3-ba5f-24f4e28619f9
                    - link "Edit rule" [ref=e961] [cursor=pointer]:
                      - /url: /rules/ad40cf24-8b99-48b3-ba5f-24f4e28619f9?edit=1
                    - button "Deactivate rule" [ref=e962] [cursor=pointer]
              - row "Aspire Carpenter xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e963]:
                - cell "Aspire" [ref=e964]
                - cell "Carpenter" [ref=e965]
                - cell "xlsx" [ref=e966]
                - cell "xlsx-master-helper-1.7" [ref=e967]:
                  - link "xlsx-master-helper-1.7" [ref=e968] [cursor=pointer]:
                    - /url: /rules/cefa3912-15b4-4cbb-bf9c-436e25de6868
                - cell "£95.00" [ref=e969]
                - cell "£119.70" [ref=e970]
                - cell "£239.40" [ref=e971]
                - cell "20%" [ref=e972]
                - cell "20%" [ref=e973]
                - cell "2024-01-01" [ref=e974]
                - cell "—" [ref=e975]
                - cell "Active" [ref=e976]
                - cell "View rule Edit rule Deactivate rule" [ref=e977]:
                  - generic [ref=e978]:
                    - link "View rule" [ref=e979] [cursor=pointer]:
                      - /url: /rules/cefa3912-15b4-4cbb-bf9c-436e25de6868
                    - link "Edit rule" [ref=e980] [cursor=pointer]:
                      - /url: /rules/cefa3912-15b4-4cbb-bf9c-436e25de6868?edit=1
                    - button "Deactivate rule" [ref=e981] [cursor=pointer]
              - row "Aspire Doors, Windows & Locks xlsx xlsx-master-helper-1.7 £95.00 £119.70 £239.40 20% 20% 2024-01-01 — Active View rule Edit rule Deactivate rule" [ref=e982]:
                - cell "Aspire" [ref=e983]
                - cell "Doors, Windows & Locks" [ref=e984]
                - cell "xlsx" [ref=e985]
                - cell "xlsx-master-helper-1.7" [ref=e986]:
                  - link "xlsx-master-helper-1.7" [ref=e987] [cursor=pointer]:
                    - /url: /rules/7b739499-24e1-4a0a-a255-2914f03b8056
                - cell "£95.00" [ref=e988]
                - cell "£119.70" [ref=e989]
                - cell "£239.40" [ref=e990]
                - cell "20%" [ref=e991]
                - cell "20%" [ref=e992]
                - cell "2024-01-01" [ref=e993]
                - cell "—" [ref=e994]
                - cell "Active" [ref=e995]
                - cell "View rule Edit rule Deactivate rule" [ref=e996]:
                  - generic [ref=e997]:
                    - link "View rule" [ref=e998] [cursor=pointer]:
                      - /url: /rules/7b739499-24e1-4a0a-a255-2914f03b8056
                    - link "Edit rule" [ref=e999] [cursor=pointer]:
                      - /url: /rules/7b739499-24e1-4a0a-a255-2914f03b8056?edit=1
                    - button "Deactivate rule" [ref=e1000] [cursor=pointer]
          - generic [ref=e1001]:
            - generic [ref=e1002]: 2528 rules
            - generic [ref=e1003]:
              - button "Previous" [disabled] [ref=e1004]
              - generic [ref=e1005]: Page 1 of 51
              - button "Next" [ref=e1006] [cursor=pointer]
```

# Test source

```ts
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
  129 |     await expect(page.getByRole("cell", { name: "Atkinson McLeod" }).first()).toBeVisible();
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
> 145 |     await page.locator("select").nth(2).selectOption("false");
      |                                         ^ Error: locator.selectOption: Test timeout of 120000ms exceeded.
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