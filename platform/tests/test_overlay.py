"""Assembly algorithm tests on a small synthetic repo, not a full upstream build."""
import json
from pathlib import Path
import pytest
from integrations.openwebui.apply_overlay import apply_overlay, git_blob, rewrite_root_imports

@pytest.fixture
def checkout(tmp_path):
    repo=tmp_path/'upstream';routes=repo/'src/routes';routes.mkdir(parents=True)
    (routes/'+layout.svelte').write_text("<script>import '../app.css'; import x from '$lib/x';</script><slot />")
    (routes/'+layout.ts').write_text('export const ssr = false;')
    (routes/'(app)').mkdir();(routes/'(app)'/'+page.svelte').write_text('<p>Native chat fixture</p>')
    (routes/'auth').mkdir();(routes/'auth'/'fixture.txt').write_text('Retained native auth')
    (repo/'LICENSE').write_text('Upstream license fixture: do not remove')
    lock={'root_layout_blob':git_blob((routes/'+layout.svelte').read_bytes()),'commit':'fixture-commit','overlay_version':'0.0.1'}
    return repo,lock

def test_preserves_upstream_routes_and_license(checkout):
    repo,lock=checkout;report=apply_overlay(repo,lock)
    assert (repo/'src/routes/(upstream)/(app)/+page.svelte').read_text()=='<p>Native chat fixture</p>'
    assert (repo/'src/routes/(upstream)/auth/fixture.txt').read_text()=='Retained native auth'
    assert "../../app.css" in (repo/'src/routes/(upstream)/+layout.svelte').read_text()
    assert "$lib/x" in (repo/'src/routes/(upstream)/+layout.svelte').read_text()
    assert (repo/'LICENSE').read_text()=='Upstream license fixture: do not remove'
    assert (repo/'src/routes/_platform/apps/meters/+page.svelte').exists()
    assert (repo/'src/lib/platform/modules/metering/MetersPage.svelte').exists()
    assert report['production_ready'] is False

def test_overlay_is_idempotent(checkout):
    repo,lock=checkout
    assert apply_overlay(repo,lock)==apply_overlay(repo,lock)

def test_overlay_rejects_foreign_upstream(checkout):
    repo,lock=checkout;lock['root_layout_blob']='wrong'
    with pytest.raises(RuntimeError,match='pinned blob'):apply_overlay(repo,lock)
    assert not (repo/'src/routes/(upstream)').exists()

def test_overlay_does_not_overwrite_user_changes(checkout):
    repo,lock=checkout;apply_overlay(repo,lock)
    (repo/'src/lib/platform/client.ts').write_text('User changes')
    with pytest.raises(RuntimeError,match='modified'):apply_overlay(repo,lock)

def test_no_react_or_twenty_imported_in_runtime(checkout):
    repo,lock=checkout;apply_overlay(repo,lock)
    for p in (repo/'src/lib/platform').rglob('*'):
        if p.is_file():
            text=p.read_text()
            assert "from 'react'" not in text and "from 'react-dom" not in text
            assert '<iframe' not in text


def test_import_rebase_does_not_touch_aliases_or_types():
    s="import '../x.css'; import y from '../foo'; import {T} from './$types'; import z from '$lib/z';"
    new=rewrite_root_imports(s)
    assert "'../../x.css'" in new and "'../../foo'" in new
    assert "'./$types'" in new and "'$lib/z'" in new
