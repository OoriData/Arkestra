Browser-based but browser-agnostic tab group manager app using Python, LLMs (e.g. LM Studio server locally). Basic outline:

* Tab Group Management: web UI where to drag & drop links into named groups
* Launch Tab Groups: Feature to launch a given tab group with a single click or command
* Integration with LLM Agents: Chat feature to integrate with local LM Studio agent to automate tasks

Key features:

* Create and manage tab groups with drag-and-drop functionality
* Launch all tabs in a group with a single click
* Drag URLs from other applications directly into your groups
* Move links between groups
* Chat with the LM Studio agent for assistance
* Browser-agnostic: works with any browser since tab launching is handled by Python

The application uses:

* Litestar for the backend API
* Vue.js for the frontend UI
* Python's webbrowser module for launching tabs
* Tailwind CSS for styling
* LM Studio API for the chat assistant

## Launching the app

```sh
pip install -Ur requirements.txt
```


```sh
python -m litestar run -p 5678
```

Useful litestar args include `--debug` and `--reload`.

# Note re page titles

We try to use the app's JavaScript layer to grab titles of added pages, but there are constraints when dealing with authenticated content and cross-origin requests

* CORS Restrictions: Browser security prevents JavaScript from directly reading content from other domains unless those sites explicitly allow it via CORS headers.
* Authentication Context: Your client-side JavaScript cannot access authenticated sessions on other domains - if a user is logged into a site in their browser, your JavaScript cannot leverage those credentials.
* Private/Auth-Required Content: Pages behind authentication will return either a login page title or an error when fetched without proper credentials.

We do our best with a a tiered approach:

* First try client-side fetch (works for CORS-friendly sites)
* If that fails, fall back to server-side fetch (works for public pages)
* If both fail, use the domain name as title

An eventual solution would be a browser extension which can access page content regardless of CORS, and can use the user's actual authentication state.
