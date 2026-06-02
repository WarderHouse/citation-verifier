# Confidentiality

`citation-verifier` looks references up in public databases, so unlike a fully
offline tool it **does use the network**. This file states exactly what leaves
your computer.

## What leaves your computer

For each reference you check, the tool sends its **title, authors, year, and
DOI** to the public lookup APIs in order to find the work:

| Action | Destination |
|---|---|
| Look up a reference | CrossRef, OpenAlex, Semantic Scholar (public APIs) |
| Resolve a DOI | doi.org |
| Full text of anything | **never sent** |
| AI / LLM service | **never contacted** |
| Telemetry / analytics | **none** |

Reference metadata is normally already-published bibliographic information. Even
so, if the titles of your unpublished references are themselves sensitive (for
example, they reveal an embargoed project), do not run this tool on them.

## Optional contact header

If you set the `CITEVERIFY_MAILTO` environment variable, that email is added to
the request to CrossRef and OpenAlex so you join their faster "polite pool". It
is sent only to those services and only when you set it.

## What stays out of version control

This repository's [.gitignore](.gitignore) excludes generated reports (`out/`)
and a `projects/` directory for your own reference lists, so nothing you check is
committed even though this repository is public.
