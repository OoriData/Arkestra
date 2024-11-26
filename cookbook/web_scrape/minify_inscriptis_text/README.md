cookbook/web_scrape/minify_inscriptis_text

- Use [httpx](https://www.python-httpx.org/) to download HTML from a web page
- Use [minify_html](https://github.com/adamchainz/django-minify-html) to reduce excess whitespace and other syntactic extras
- Use [inscriptis](https://github.com/weblyzard/inscriptis) to convert the HTML into more LLM-readable form
    - inscriptis supports semantic annotations, but in this case we just use [selectolax](https://github.com/rushter/selectolax) preprocesing to make sure link hrefs aren't lost
- Check the token count & truncate if necessary
- Feed the result to [Toolio](https://github.com/OoriData/Toolio) in for LLM processing, with structured output

# Arkestra components used

* `components.prompt.load_loom`

# Usage

```sh
python main.py https://africandreamfoods.com/collections/all-products
```

Beware of sites whose design make it tricky for the LLM, and probably lead to an excess of prompt tokens

An example: https://www.milehighdjsupply.com/shop-by-category/records/skratch-records/

# Inspiration

[m92vyas/llm-reader](https://github.com/m92vyas/llm-reader)

# Implementation notes:

Fully articulated, the output schema sections would look like:

```json
            "Product Link": {
                "type": "string",
                "format": "uri",
                "description": "Direct link to product page"
            },
            "Image Link": {
                "type": "string", 
                "format": "uri",
                "description": "URL of product image"
            },
            "Price": {
                "type": "string",
                "description": "Product price in US Dollars",
                "pattern": "^$\\.[0-9,]+$"
            }
```

But we don't support string format specifiers or patterns (and that would be a fair stretch)

See also:

* Tools such as [Scrapergraph](https://github.com/ScrapeGraphAI/Scrapegraph-ai)
