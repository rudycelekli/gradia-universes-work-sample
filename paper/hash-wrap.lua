-- Permit exact 64-character SHA-256 values to wrap without changing the source.
function Code(element)
  if string.match(element.text, "^[0-9a-f][0-9a-f]+$") and string.len(element.text) == 64 then
    return pandoc.RawInline("latex", "\\texttt{\\seqsplit{" .. element.text .. "}}")
  end
  return element
end

local first_claim_boundary = true

function BlockQuote(element)
  if first_claim_boundary then
    first_claim_boundary = false
    return {pandoc.RawBlock("latex", "\\newpage"), element}
  end
  return element
end
