# Releasing

Releases are cut from a git tag. Pushing a tag `vX.Y.Z` triggers
`.github/workflows/release.yml`, which tests, builds, and creates a GitHub Release.

## Versioning policy (SemVer)

The version lives in `pyproject.toml` (`project.version`) and follows
[Semantic Versioning](https://semver.org). For this CLI the public interface is the
command-line behavior: stdin format, stdout format, exit codes, and the interaction data
semantics.

- MAJOR: breaking change to input or output format, exit codes, or how severity/ordering is
  resolved, or dropping a supported Python version.
- MINOR: backwards-compatible features, e.g. new options or new supported input forms.
- PATCH: backwards-compatible bug fixes, docs, and internal changes.

Pre-releases use PEP 440 suffixes such as `1.0.0rc1`; tag them `v1.0.0rc1`. Note that uv
normalizes `1.0.0-rc.1` to `1.0.0rc1`, so use the normalized form in the tag.

## Release steps

1. Make sure `main` is green and up to date.
2. Bump the version (updates `pyproject.toml` and `uv.lock`):

   ```sh
   uv version --bump patch   # or minor / major
   uv version --short        # prints the new version, e.g. 0.1.1
   ```

   For a pre-release: `uv version 1.0.0rc1`.
3. Commit and push via a PR (or directly if permitted):

   ```sh
   git commit -am "Release vX.Y.Z"
   ```
4. After that commit is on `main`, tag it and push the tag:

   ```sh
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

## What the workflow does

1. Checks out the tag and installs Python (from `.python-version`) and locked dependencies.
2. Fails if the tag does not equal `v` + `project.version`.
3. Runs the test suite.
4. Runs `uv build` (sdist and wheel).
5. Creates a GitHub Release for the tag with auto-generated notes, attaching `dist/*`.
   Versions that are not plain `X.Y.Z` are marked as pre-releases.

The workflow can also be run manually (Actions, Release, Run workflow) with the name of an
existing tag. Nothing is published to PyPI.

## Installing a released wheel

```sh
uv tool install https://github.com/evonnec/interactions/releases/download/vX.Y.Z/interactions-X.Y.Z-py3-none-any.whl
interactions < input.txt
```

The wheel is named `interactions-<version>-py3-none-any.whl`. For a private repository,
download the asset with `gh release download vX.Y.Z -R evonnec/interactions` and install the
local file instead.

## Optional: publishing to PyPI later

Not enabled. To publish with PyPI Trusted Publishing (no API tokens):

1. On pypi.org, go to Your projects, Publishing, and add a pending publisher with: PyPI
   project name `interactions` (check the name is available, or choose another), owner
   `evonnec`, repository `interactions`, workflow filename `release.yml` (or a dedicated
   `publish.yml`), and environment `pypi`.
2. In the GitHub repo, Settings, Environments, create an environment named `pypi`
   (optionally with required reviewers).
3. Add a job to the release workflow, after the build job, that downloads the built `dist/`
   and publishes it:

   ```yaml
   publish-pypi:
     needs: release
     runs-on: ubuntu-latest
     environment: pypi
     permissions:
       id-token: write
     steps:
       - uses: actions/download-artifact@<version>
         with:
           name: dist
           path: dist/
       - uses: astral-sh/setup-uv@<version>
       - run: uv publish --trusted-publishing always
   ```

   (This requires the release job to upload `dist/` with `actions/upload-artifact`.
   Alternatively use `pypa/gh-action-pypi-publish`.) Pin actions to current release tags.
4. Fill in project metadata (authors, URLs) in `pyproject.toml` before the first upload.
