Add-Type -AssemblyName PresentationFramework
$form = New-Object System.Windows.Window
$form.Title = 'Screen Record address-bar test'
$form.Width = 500
$form.Height = 150
$panel = New-Object System.Windows.Controls.StackPanel
$search = New-Object System.Windows.Controls.TextBox
[System.Windows.Automation.AutomationProperties]::SetName($search, 'Search')
$search.Text = 'https://wrong.example/'
$panel.Children.Add($search) | Out-Null
$address = New-Object System.Windows.Controls.TextBox
[System.Windows.Automation.AutomationProperties]::SetName($address, 'Address and search bar')
$address.Text = 'https://example.com/a/b?q=hello&x=1'
$panel.Children.Add($address) | Out-Null
$scroll = New-Object System.Windows.Controls.ScrollViewer
$scroll.Height = 60
$scroll.VerticalScrollBarVisibility = 'Auto'
$long = New-Object System.Windows.Controls.TextBlock
$long.Text = ((1..100 | ForEach-Object { "Line $_" }) -join "`n")
$scroll.Content = $long
$panel.Children.Add($scroll) | Out-Null
$form.Content = $panel
$form.Add_ContentRendered({
    $helper = New-Object System.Windows.Interop.WindowInteropHelper($form)
    [Console]::WriteLine($helper.Handle.ToInt64())
})
$form.ShowDialog() | Out-Null
