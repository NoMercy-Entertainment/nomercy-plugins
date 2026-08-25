# NoMercy Plugins

The plugin index every NoMercy media server reads by default.

A server fetches [`index.json`](index.json), shows what it lists under Dashboard > Plugins >
Catalogue, and installs from there.

```
https://raw.githubusercontent.com/NoMercy-Entertainment/nomercy-plugins/master/index.json
```

**`index.json` is generated. Do not edit it by hand.** It is built from
[`sources.json`](sources.json) by [`tools/build-index.py`](tools/build-index.py), which runs
on a schedule and whenever `sources.json` changes.

## Listing your plugin

Two steps, and the second happens once in the life of your plugin.

### 1. Publish an index of your own

One JSON file, on any https host, at a URL that does not move — the raw view of a file in
your own repository is ideal. It lists every version you have released:

```json
{
  "name": "Example Plugin",
  "url": "https://example.com/you/example-plugin",
  "plugins": [
    {
      "id": "1SBQT26FHF98EBRPYVRGD92CZF",
      "name": "Example Plugin",
      "description": "What this plugin does, in one line.",
      "author": "Your name",
      "projectUrl": "https://example.com/you/example-plugin",
      "versions": [
        {
          "version": "1.0.0",
          "targetAbi": "10.0",
          "downloadUrl": "https://example.com/you/example-plugin/releases/download/v1.0.0/Example.Plugin-1.0.0.zip",
          "checksum": "sha256 of that file, lowercase hex",
          "changelog": "First release.",
          "timestamp": "2026-07-30T00:00:00Z"
        }
      ]
    }
  ]
}
```

Validate it against [`schema.json`](schema.json). Let your own CI write it when you cut a
release, so it can never disagree with what you shipped.

### 2. Add its URL here

Open a pull request adding one entry to `sources.json`:

```json
{ "name": "Example Plugin", "url": "https://example.com/you/example-plugin/raw/master/repository.json" }
```

That is the whole submission, and **you never have to come back for a new release**. Ship
1.1.0, let your CI add it to your own index, and this catalogue picks it up on its next run.

The alternative — a pull request here for every version — is what this replaced. It is why
the catalogue offered a plugin three versions deep whose own CI knew nothing about any of
them.

## What gets checked

A pull request is validated before anyone reads it, and the same checks run on every rebuild.

`id` must be your plugin's **Ulid** — twenty-six characters of Crockford base32, exactly the
id in your `plugin.json`. **It is not a GUID.** `IPlugin.Id` is a `Ulid`; this repository's
schema asked for a `uuid` until 25 August 2026 while every plugin listed used a Ulid. It is
the identity a server uses to tell an update from a different plugin, so a mismatch means
updates never land.

`downloadUrl` must be a direct https link to your plugin's **zip**, and it has to keep
working. The server fetches it, verifies it and extracts it — `PluginManager` opens the
download as a zip archive. Not a bare `.dll`: a plugin is a folder of assemblies and its
manifest, and a folder missing its dependencies fails to load with nothing said about why.

`checksum` is optional and you should publish it anyway. The server verifies the file before
anything is copied into place. Without one, the catalogue marks the version unverified and
tells the owner so in the confirmation prompt.

You host your own binaries. This repository points at them and never mirrors them, so you
keep control of your releases and nothing here goes stale when you cut a new one.

## What the generator will not do

**It never deletes.** A version already in `index.json` stays, even if no source mentions it.
The entries that predate `sources.json` carry changelogs nothing can regenerate, and a source
that is briefly offline must not empty the catalogue.

**It never invents.** Everything written comes from a source or was already there. A source
that cannot be read is reported and skipped, and the rest is built without it.

## Hosting your own index

You do not need this repository. An index is one JSON file on any https host, and a server
owner can add yours by URL. See
[Publishing a Plugin Repository](https://docs.nomercy.tv/nomercy-media-server/plugins/repository-index).

## What being listed does not grant

Nothing. A plugin still declares its capabilities in its own manifest, still installs
disabled when it asks for more than the baseline, and still waits for the server owner to
approve what it asked for. This index is a place to find plugins, not a way around consent.
