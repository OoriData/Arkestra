
# Features

* Rich progress bars and status indicators
* Content type classification
* Proper HTML-to-markdown conversion using trafilatura
  * Preparation for handling different content types (PDFs, images, etc.)

# Setup

## SearXNG

Running [SearXNG](https://github.com/searxng/searxng) instance. You can just use the Docker container. To run this locally:

```sh
docker pull searxng/searxng
export SEARXNG_PORT=8888
docker run \
    -d -p ${SEARXNG_PORT}:8080 \
    -v "${PWD}/searxng:/etc/searxng" \
    -e "BASE_URL=http://localhost:$SEARXNG_PORT/" \
    -e "INSTANCE_NAME=tee-seeker-searxng" \
    --name tee-seeker-searxng \
    searxng/searxng
```

Note: We want to have some sort of API key, but doesn't seem there is any built-in approach (`SEARXNG_SECRET` is something different). We might have to use a reverse proxy with HTTP auth.

This gets SearXNG runing on port 8888. Feel free to adjust as necessary in the 10minclimate.com config.

You do need to edit `searxng/settings.yml` relative to where you launched the docker comtainer, making sure `server.limiter` is set to false and `- json` is included in `search.formats`.

You can then just restart the continer (use `docker ps` to get the ID, `docker stop [ID]` and then repeat the `docker run` command above).

<!-- Not needed at present
One trick for generating a secret key:

```sh
python -c "from uuid import uuid1; print(str(uuid1()))"
```
-->

### Clean up

```sh
docker stop researcher-searxng
# And only if you're done with it:
docker rm researcher-searxng
```

# Running

```sh
time python main.py "What's so valuable about DeepSeek's GRPO technique?" --rigor 0.1
```


# See also

* [Introducing Deeper Seeker - A simpler and OSS version of OpenAI's latest Deep Research feature](https://www.reddit.com/r/LocalLLaMA/comments/1igyy0n/introducing_deeper_seeker_a_simpler_and_oss/) [Feb 2025]

# To do

- Future integration with PDF processors e.g. PyPDF2 or pdfplumber
- Integration with vision models for image content
- Adding content summarization for long texts
- Better content extraction and cleaning
- Implementing parallel processing for content fetching
- More informative progress tracking
- Better error handling and logging
- Adding content caching to avoid re-downloading
