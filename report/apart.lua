-- Pandoc filter for report/report.md (iteration 13, D133).
-- LaTeX: the Div of class "abstract" becomes the template's apartabstract environment (centred heading, narrower
-- measure); its "Abstract" heading is dropped because the environment prints it.  Other formats: unchanged.
function Div(el)
  if not el.classes:includes("abstract") or not FORMAT:match("latex") then return nil end
  local blocks = {pandoc.RawBlock("latex", "\\begin{apartabstract}")}
  for _, b in ipairs(el.content) do
    if b.t ~= "Header" then table.insert(blocks, b) end
  end
  table.insert(blocks, pandoc.RawBlock("latex", "\\end{apartabstract}"))
  return blocks
end
