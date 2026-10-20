param([Parameter(Mandatory=$true)][string]$DataRoot,[Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]{1,100}$')][string]$TemplateId,[int]$ParentProcessId=0)
$ErrorActionPreference='Stop'
$utf8=New-Object Text.UTF8Encoding($false)
$path=Join-Path $DataRoot ('Templates\'+$TemplateId+'.docx')
$output=Join-Path $DataRoot ('Templates\'+$TemplateId+'.sync.json')
$active=Join-Path $DataRoot 'Temp\session.active'
$session=[IO.File]::ReadAllText($active)
$last=''
function Publish($payload){
 $temp=$output+'.tmp';[IO.File]::WriteAllText($temp,($payload|ConvertTo-Json -Depth 20 -Compress),$utf8)
 if(Test-Path $output){[IO.File]::Replace($temp,$output,$null)}else{[IO.File]::Move($temp,$output)}
}
while(($ParentProcessId -eq 0 -or (Get-Process -Id $ParentProcessId -ErrorAction SilentlyContinue)) -and (Test-Path $active) -and [IO.File]::ReadAllText($active) -eq $session){
 try{
  if(-not(Test-Path $path)){break}
  # Read a consistent on-disk Word save. File sharing tolerates an open document.
  $fs=New-Object IO.FileStream($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
  try{$ms=New-Object IO.MemoryStream;$fs.CopyTo($ms);$raw=$ms.ToArray();$ms.Dispose()}finally{$fs.Dispose()}
  $sha=[Security.Cryptography.SHA256]::Create();try{$revision=[BitConverter]::ToString($sha.ComputeHash($raw)).Replace('-','')}finally{$sha.Dispose()}
  if($revision -ne $last){
   $tempDir=Join-Path $DataRoot ('Temp\word-'+$TemplateId+'-'+[Guid]::NewGuid().ToString('N'))
   [void][IO.Directory]::CreateDirectory($tempDir)
   $copy=Join-Path $tempDir 'source.docx';$htmlPath=Join-Path $tempDir 'template.html';[IO.File]::WriteAllBytes($copy,$raw)
   $word=$null;$doc=$null
   try{
    $word=New-Object -ComObject Word.Application
    $word.Visible=$false;$word.DisplayAlerts=0;$word.AutomationSecurity=3
    $doc=$word.Documents.Open($copy,$false,$true,$false)
    $setup=$doc.PageSetup
    $page=@{margins=@{top=[Math]::Round($setup.TopMargin*25.4/72,2);right=[Math]::Round($setup.RightMargin*25.4/72,2);bottom=[Math]::Round($setup.BottomMargin*25.4/72,2);left=[Math]::Round($setup.LeftMargin*25.4/72,2)};orientation=if($setup.Orientation -eq 1){'landscape'}else{'portrait'};pageSize=if($setup.PaperSize -eq 11){'A5'}else{'A4'}}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($setup)
    # wdFormatFilteredHTML = 10. Convert a copy, never the user's active document.
    $doc.WebOptions.Encoding=65001
    $doc.SaveAs2($htmlPath,10)
    $html=[IO.File]::ReadAllText($htmlPath,$utf8)
    # Word stores headers and footers separately in HTML exports.
    $headerFile=Get-ChildItem $tempDir -Recurse -Filter 'header.htm'|Select-Object -First 1
    if($headerFile){
     $hf=[IO.File]::ReadAllText($headerFile.FullName,$utf8)
     $hb=[regex]::Match($hf,'(?is)<body[^>]*>(.*?)</body>').Groups[1].Value
     if($hb){$html=$html -replace '(?i)(<body[^>]*>)',('$1'+[string]$hb.Replace('$','$$')))}
    }
    # Inline exported image assets so templates persist without temp-file links.
    $html=[regex]::Replace($html,'(?is)(\bsrc\s*=\s*["''])([^"'']+)(["''])',[Text.RegularExpressions.MatchEvaluator]{param($m)
     $relative=[Uri]::UnescapeDataString($m.Groups[2].Value).Replace('/',[IO.Path]::DirectorySeparatorChar)
     $image=Join-Path $tempDir $relative
     if(-not(Test-Path $image) -and $headerFile){ $image=Join-Path (Split-Path $headerFile.FullName -Parent) $relative }
     if((Test-Path $image) -and [IO.Path]::GetFullPath($image).StartsWith([IO.Path]::GetFullPath($tempDir)+[IO.Path]::DirectorySeparatorChar)){
      $ext=[IO.Path]::GetExtension($image).TrimStart('.').ToLowerInvariant();if($ext -eq 'jpg'){$ext='jpeg'}
      if($ext -in @('png','jpeg','gif','webp')){return $m.Groups[1].Value+'data:image/'+$ext+';base64,'+[Convert]::ToBase64String([IO.File]::ReadAllBytes($image))+$m.Groups[3].Value}
     }
     return $m.Value
    })
    Publish @{id=$TemplateId;revision=$revision;html=$html;bytes=[Convert]::ToBase64String($raw);page=$page}
    $last=$revision
   }finally{
    if($doc){try{$doc.Close(0)}catch{};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)}
    if($word){try{$word.Quit()}catch{};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
   }
  }
 }catch{
  $last=''
  Publish @{id=$TemplateId;revision='error-'+$revision;error='Word changes could not be translated. Save and close the template in Word, then retry. '+$_.Exception.Message}
 }
 Start-Sleep -Seconds 2
}
