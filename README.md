# NoMercy Plugins

The plugin index every NoMercy media server reads by default.

A server fetches [`index.json`](index.json), shows what it lists under Dashboard > Plugins >
Catalogue, and installs from there. That is the whole mechanism. This repository holds the
file and nothing else.

```
https://raw.githubusercontent.com/NoMercy-Entertainment/nomercy-plugins/master/index.json
```

## Listing your plugin

Open a pull request that adds an entry to `plugins` in `index.json`. Validate it against
[`schema.json`](schema.json) before you do; a malformed entry is rejected in review, and a
malformed index would take the whole catalogue down for everyone reading it.

```json
{
  "id": "6f9619ff-8b86-d011-b42d-00cf4fc964ff",
  "name": "Example.Plugin",
  "description": "What this plugin does, in one line.",
  "author": "Your name",
  "projectUrl": "https://github.com/you/example-plugin",
  "versions": [
    {
      "version": "1.0.0",
      "targetAbi": "1.0",
      "downloadUrl": "https://github.com/you/example-plugin/releases/download/v1.0.0/Example.Plugin.dll",
      "checksum": "sha256 of that file, lowercase hex",
      "changelog": "First release.",
      "timestamp": "2026-07-30T00:00:00Z"
    }
  ]
}
```

Four things get checked in review.

`id` has to match the GUID in your plugin's own `plugin.json`. It is the identity a server
uses to tell an update from a different plugin, so a mismatch means updates never land.

`downloadUrl` has to be a direct link to the `.dll` over https, and it has to keep working.
A release asset URL is fine; a link to a page with a download button on it is not.

`checksum` is optional and you should publish it anyway. The server verifies the file before
anything is copied into place. Without one, the catalogue marks the version unverified and
tells the owner so in the confirmation prompt.

You host your own binaries. This repository points at them and never mirrors them, so you
keep control of your releases and nothing here goes stale when you cut a new one.

## Hosting your own index

You do not need this repository. An index is one JSON file on any https host, and a server
owner can add yours by URL. See
[Publishing a Plugin Repository](https://docs.nomercy.tv/nomercy-media-server/plugins/repository-index).

## What being listed does not grant

Nothing. A plugin still declares its capabilities in its own manifest, still installs
disabled when it asks for more than the baseline, and still waits for the server owner to
approve what it asked for. This index is a place to find plugins, not a way around consent.
