# FILTERS

Various regex and useful things I come across or write

## Disable SRI

* Script tags, response body: `\sintegrity="[^"]"`
* Dynamic creation, response body: `(\w+\.)?(integrity=)([^,]+),?`
