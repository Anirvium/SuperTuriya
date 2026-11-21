# Share and run the SuperTuriya website

The website is already published with public access:

- Website: https://superturiya.piyushunt.chatgpt.site
- Interactive demo: https://superturiya.piyushunt.chatgpt.site/demo/
- Guide: https://superturiya.piyushunt.chatgpt.site/docs/

Share the website URL in your Threads bio and posts. Visitors can open the site
and recorded playground without signing in. Hosting runs independently of your
computer; your computer does not need to stay on.

## Preview the website on your computer

From the SuperTuriya project folder, run:

```bash
python3 -m http.server 8787 --bind 127.0.0.1 --directory sites/superturiya/dist
```

On Windows, use `py` in place of `python3`. Open
http://127.0.0.1:8787 in a browser. Keep the terminal open while previewing;
press Ctrl+C to stop it. This local preview does not publish changes.

To download the release on another computer with Git and Python installed:

```bash
git clone --branch launch/cosmic-workbench-2026-11-21 https://github.com/Anirvium/SuperTuriya.git
cd SuperTuriya
python3 -m http.server 8787 --bind 127.0.0.1 --directory sites/superturiya/dist
```

## Run the Python operator

For local replay execution and persisted policy decisions, run from the project
folder in a separate terminal:

```bash
python3 -m superturiya --seed --port 8765
```

Open http://127.0.0.1:8765. The public demo uses recorded synthetic results;
the local operator executes the Python workflow.

## Engagement and visibility

The live website includes a product explanation, interactive demo, documentation,
share-preview image, search metadata, robots.txt and a sitemap. Search engines
decide when to crawl and index it; publication does not guarantee search ranking.

The workflow-conversation button opens a GitHub issue draft. The visitor needs a
GitHub account to submit it. There is currently no email signup, visitor analytics,
or private lead database. For engagement now, invite replies on your Threads post
and point curious visitors to the playground.

Suggested launch text:

> I'm building SuperTuriya to help AI agents learn from failure with evidence,
> tested repairs, and human approval. Try the interactive playground—no signup
> needed. What failure would you want your agent to learn from?
> https://superturiya.piyushunt.chatgpt.site

## Publish future website changes

Website files live in `sites/superturiya/dist`. Updating local files or pushing
the product's GitHub branch does not automatically update the live website.
Use the existing Sites project identified in
`sites/superturiya/.openai/hosting.json` to package and publish a new version.
The live URL stays the same.
