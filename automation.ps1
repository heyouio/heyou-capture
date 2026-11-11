Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName UIAutomationClientSideProviders
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$ErrorActionPreference = 'Stop'
$root = $null
$pattern = $null
:requests while ($line = [Console]::ReadLine()) {
    try {
        $request = $line | ConvertFrom-Json
        switch ($request.action) {
            'tabs' {
                $browser = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$request.hwnd)
                $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
                $pending = New-Object 'System.Collections.Generic.Queue[System.Windows.Automation.AutomationElement]'
                $pending.Enqueue($browser)
                $tabs = New-Object 'System.Collections.Generic.List[System.Windows.Automation.AutomationElement]'
                $items = @()
                $originalTab = -1
                while ($pending.Count -gt 0) {
                    $element = $pending.Dequeue()
                    if ($element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document) { continue }
                    if ($element.Current.ControlType -eq [System.Windows.Automation.ControlType]::TabItem) {
                        $selection = $null
                        if ($element.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$selection)) {
                            $index = $tabs.Count
                            if ($selection.Current.IsSelected) { $originalTab = $index }
                            $tabs.Add($element)
                            $items += @{ index = $index; title = $element.Current.Name }
                        }
                        continue
                    }
                    $child = $walker.GetFirstChild($element)
                    while ($null -ne $child) {
                        $pending.Enqueue($child)
                        $child = $walker.GetNextSibling($child)
                    }
                }
                if ($tabs.Count -eq 0) { throw 'No browser tabs could be read in this window.' }
                @{ ok = $true; tabs = @($items); original = $originalTab } | ConvertTo-Json -Compress -Depth 4
                continue requests
            }
            'select_tab' {
                $tab = $tabs[[int]$request.index]
                $selection = $tab.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
                $selection.Select()
                $tab.SetFocus()
                $pattern = $null
                @{ ok = $true } | ConvertTo-Json -Compress
                continue requests
            }
            'tab_selected' {
                $selection = $tabs[[int]$request.index].GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
                @{ ok = $true; selected = $selection.Current.IsSelected } | ConvertTo-Json -Compress
                continue requests
            }
            'url' {
                $browser = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$request.hwnd)
                # Walk browser chrome only. Never mistake an input in the web
                # document for the address bar, including on localized browsers.
                $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
                $pending = New-Object 'System.Collections.Generic.Queue[System.Windows.Automation.AutomationElement]'
                $pending.Enqueue($browser)
                $url = $null
                $visited = 0
                while ($pending.Count -gt 0 -and $visited -lt 1500 -and !$url) {
                    $element = $pending.Dequeue()
                    $visited++
                    if ($element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document) { continue }
                    if ($element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Edit -and !$element.Current.IsOffscreen -and !$element.Current.IsPassword) {
                        $valuePattern = $null
                        if ($element.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$valuePattern)) {
                            $value = $valuePattern.Current.Value
                            $id = $element.Current.AutomationId
                            $name = $element.Current.Name
                            $isAddress = $id -match '(?i)urlbar|address|omnibox|location' -or $name -match '(?i)address|url|location'
                            if ($isAddress -and $value -and ($value -match '^\w[\w+.-]*:' -or $value -match '^[^\s/]+[.:][^\s]+')) {
                                $url = $value
                                break
                            }
                        }
                    }
                    $child = $walker.GetFirstChild($element)
                    while ($null -ne $child) {
                        $pending.Enqueue($child)
                        $child = $walker.GetNextSibling($child)
                    }
                }
                if (!$url) { throw 'Could not read the browser address bar. Show the address bar and use a supported Chrome or Edge window, then retry.' }
                @{ ok = $true; url = $url } | ConvertTo-Json -Compress
                continue requests
            }
            'attach' {
                $root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$request.hwnd)
                $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::IsScrollPatternAvailableProperty, $true)
                $elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
                $best = 0
                $pattern = $null
                foreach ($element in $elements) {
                    if ($element.Current.IsOffscreen) { continue }
                    $candidate = $element.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
                    $rect = $element.Current.BoundingRectangle
                    $area = $rect.Width * $rect.Height
                    if ($candidate.Current.VerticallyScrollable) { $area += 1000000000000 }
                    if ($area -gt $best) {
                        $best = $area
                        $pattern = $candidate
                    }
                }
                if ($null -eq $pattern) { throw 'This browser page does not expose readable scrolling controls. Capture stopped rather than saving an incomplete page.' }
                $original = $pattern.Current.VerticalScrollPercent
            }
            'scroll' { if ($pattern.Current.VerticallyScrollable) { $pattern.SetScrollPercent(-1, [double]$request.percent) } }
            'restore' { if ($null -ne $pattern -and $original -ge 0 -and $pattern.Current.VerticallyScrollable) { $pattern.SetScrollPercent(-1, $original) } }
            'status' { }
            default { throw 'Unknown action' }
        }
        @{ ok = $true; percent = $pattern.Current.VerticalScrollPercent; view = $pattern.Current.VerticalViewSize; scrollable = ($null -ne $pattern -and $pattern.Current.VerticallyScrollable) } | ConvertTo-Json -Compress
    } catch {
        @{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress
    }
}
