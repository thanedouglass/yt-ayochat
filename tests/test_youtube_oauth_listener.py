"""Unit tests for YouTube API OAuth 2.0 and Comment Listener."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from src.pipeline.listener import YouTubeCommentListener, CommentTriggerFilter
from src.pipeline.dispatcher import ActionDispatcher
from src.pipeline.auth import get_authenticated_channel_id


def test_comment_listener_author_reply_filtering():
    """Test that YouTubeCommentListener filters out comments that the author has already replied to."""
    mock_client = MagicMock()
    
    # Mock channels().list().execute()
    mock_channels_list = MagicMock()
    mock_channels_list.execute.return_value = {
        "items": [{"id": "UC_author_123"}]
    }
    mock_client.channels.return_value.list.return_value = mock_channels_list

    # Mock commentThreads().list().execute()
    mock_threads_list = MagicMock()
    mock_threads_list.execute.return_value = {
        "items": [
            {
                "id": "thread_no_replies",
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": "How do I deploy this?",
                            "authorDisplayName": "UserA",
                            "authorChannelId": {"value": "UC_user_a"},
                            "publishedAt": "2026-08-25T12:00:00Z"
                        }
                    },
                    "totalReplyCount": 0
                }
            },
            {
                "id": "thread_other_replies",
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": "What model should I use?",
                            "authorDisplayName": "UserB",
                            "authorChannelId": {"value": "UC_user_b"},
                            "publishedAt": "2026-08-25T12:05:00Z"
                        }
                    },
                    "totalReplyCount": 1
                }
            },
            {
                "id": "thread_author_replied",
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": "Where is the documentation?",
                            "authorDisplayName": "UserC",
                            "authorChannelId": {"value": "UC_user_c"},
                            "publishedAt": "2026-08-25T12:10:00Z"
                        }
                    },
                    "totalReplyCount": 1
                }
            }
        ]
    }
    mock_client.commentThreads.return_value.list.return_value = mock_threads_list

    # Mock comments().list().execute() for thread replies check
    mock_comments_list = MagicMock()
    
    def mock_comments_list_side_effect(part, parentId, maxResults=100):
        mock_exec = MagicMock()
        if parentId == "thread_other_replies":
            mock_exec.execute.return_value = {
                "items": [
                    {
                        "snippet": {
                            "authorChannelId": {"value": "UC_user_x"},
                            "textOriginal": "I also want to know!"
                        }
                    }
                ]
            }
        elif parentId == "thread_author_replied":
            mock_exec.execute.return_value = {
                "items": [
                    {
                        "snippet": {
                            "authorChannelId": {"value": "UC_author_123"},
                            "textOriginal": "Check the docs here: 📌 Source..."
                        }
                    }
                ]
            }
        else:
            mock_exec.execute.return_value = {"items": []}
        return mock_exec

    mock_client.comments.return_value.list.side_effect = mock_comments_list_side_effect

    # Set require_question=False to process all triggering or regular texts
    filter_fn = CommentTriggerFilter(require_question=False)
    listener = YouTubeCommentListener(youtube_client=mock_client, filter_fn=filter_fn)

    comments = listener.poll_video_comments("dummy_video")
    
    assert len(comments) == 2
    assert comments[0].comment_id == "thread_no_replies"
    assert comments[1].comment_id == "thread_other_replies"


def test_action_dispatcher_insert():
    """Test that ActionDispatcher calls comments().insert() with correct parameters."""
    mock_client = MagicMock()
    mock_insert = MagicMock()
    mock_insert.execute.return_value = {"id": "reply_id_123"}
    mock_client.comments.return_value.insert.return_value = mock_insert

    dispatcher = ActionDispatcher(youtube_client=mock_client)
    
    with patch.object(dispatcher.guardrails, "verify_output") as mock_verify:
        mock_verify.return_value.is_valid = True
        
        result = dispatcher.dispatch_reply(
            comment_id="comment_abc",
            reply_text="Here is the response. 📌 Source: Docs (Reference: 01)"
        )
        
        assert result.reply_id == "reply_id_123"
        mock_client.comments.return_value.insert.assert_called_once_with(
            part="snippet",
            body={
                "snippet": {
                    "parentId": "comment_abc",
                    "textOriginal": "Here is the response. 📌 Source: Docs (Reference: 01)"
                }
            }
        )


def test_log_to_synthetic_memory_and_dual_corpus(tmp_path, monkeypatch):
    """Verify log_to_synthetic_memory writes correctly formatted JSONL entries."""
    import json
    from src.pipeline.dispatcher import log_to_synthetic_memory

    synth_file = tmp_path / "lumi_synthetic_memory.jsonl"
    monkeypatch.chdir(tmp_path)

    log_to_synthetic_memory(
        category="DANCE_CHOREO",
        input_comment="that footwork transition at 0:15 was insane!",
        lumi_response="That footwork transition took three whole studio sessions to drill without twisting my ankle!",
        intent="CHOREO_PRAISE",
        energy=5,
    )

    assert synth_file.exists()
    lines = synth_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["id"].startswith("LUMI-SYNTH-")
    assert data["category"] == "DANCE_CHOREO"
    assert data["input_comment"] == "that footwork transition at 0:15 was insane!"
    assert data["context_lore"] == "Autonomously generated via Swarm routing"
    assert data["lumi_response"] == "That footwork transition took three whole studio sessions to drill without twisting my ankle!"
    assert data["semiotic_intent"] == "CHOREO_PRAISE"
    assert data["energy_level"] == 5


def test_auth_gitignore_security():
    """Verify that .gitignore strictly contains client_secret.json and token.json."""
    import subprocess
    from pathlib import Path
    
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore file must exist"
    content = gitignore_path.read_text()
    
    assert "client_secret.json" in content
    assert "token.json" in content

    # Test git check-ignore
    result = subprocess.run(
        ["git", "check-ignore", "client_secret.json", "token.json"],
        capture_output=True,
        text=True,
    )
    assert "client_secret.json" in result.stdout
    assert "token.json" in result.stdout


def test_auth_missing_client_secret(monkeypatch, tmp_path):
    """Verify that a missing client_secret.json raises FileNotFoundError with actionable instructions."""
    from src.pipeline import auth
    
    fake_token = tmp_path / "nonexistent_token.json"
    fake_secret = tmp_path / "nonexistent_secret.json"
    
    monkeypatch.setattr(auth.config, "token_path", str(fake_token))
    monkeypatch.setattr(auth.config, "client_secret_path", str(fake_secret))
    
    with pytest.raises(FileNotFoundError) as exc_info:
        auth.get_credentials()
        
    assert "OAuth client secrets file" in str(exc_info.value)
    assert "missing" in str(exc_info.value)
    assert "Google Cloud Console" in str(exc_info.value)


def test_auth_malformed_client_secret(monkeypatch, tmp_path):
    """Verify that a malformed client_secret.json raises ValueError with clear error details."""
    from src.pipeline import auth
    
    fake_token = tmp_path / "nonexistent_token.json"
    fake_secret = tmp_path / "malformed_secret.json"
    fake_secret.write_text("{ not valid json")
    
    monkeypatch.setattr(auth.config, "token_path", str(fake_token))
    monkeypatch.setattr(auth.config, "client_secret_path", str(fake_secret))
    
    with pytest.raises(ValueError) as exc_info:
        auth.get_credentials()
        
    assert "invalid or malformed" in str(exc_info.value)


def test_auth_cached_valid_token(monkeypatch, tmp_path):
    """Verify that valid cached credentials in token.json are loaded without initiating OAuth flow."""
    from src.pipeline import auth
    
    fake_token = tmp_path / "token.json"
    fake_token.write_text('{"token": "mock_access_token"}')
    
    mock_creds = MagicMock()
    mock_creds.valid = True
    
    monkeypatch.setattr(auth.config, "token_path", str(fake_token))
    
    with patch("src.pipeline.auth.Credentials.from_authorized_user_file", return_value=mock_creds) as mock_load:
        creds = auth.get_credentials()
        assert creds == mock_creds
        mock_load.assert_called_once_with(str(fake_token), auth.SCOPES)


def test_auth_expired_token_refreshes(monkeypatch, tmp_path):
    """Verify that an expired token with a refresh token is automatically refreshed."""
    from src.pipeline import auth
    
    fake_token = tmp_path / "token.json"
    fake_token.write_text('{"token": "expired_token"}')
    
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "valid_refresh_token"
    mock_creds.to_json.return_value = '{"token": "refreshed_token"}'
    
    monkeypatch.setattr(auth.config, "token_path", str(fake_token))
    
    with patch("src.pipeline.auth.Credentials.from_authorized_user_file", return_value=mock_creds):
        creds = auth.get_credentials()
        assert creds == mock_creds
        mock_creds.refresh.assert_called_once()


def test_auth_full_oauth_flow_and_token_cache(monkeypatch, tmp_path):
    """Verify full OAuth 2.0 flow initialization, scope validation, and token caching."""
    from src.pipeline import auth
    
    fake_token = tmp_path / "token.json"
    fake_secret = tmp_path / "client_secret.json"
    fake_secret.write_text('{"installed": {"client_id": "123", "client_secret": "abc"}}')
    
    monkeypatch.setattr(auth.config, "token_path", str(fake_token))
    monkeypatch.setattr(auth.config, "client_secret_path", str(fake_secret))
    
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = '{"token": "newly_authorized_token"}'
    
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    
    with patch("src.pipeline.auth.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow) as mock_flow_init:
        creds = auth.get_credentials()
        
        # Verify scope and client secrets file
        mock_flow_init.assert_called_once_with(str(fake_secret), ["https://www.googleapis.com/auth/youtube.force-ssl"])
        
        # Verify run_local_server parameters
        mock_flow.run_local_server.assert_called_once()
        _, kwargs = mock_flow.run_local_server.call_args
        assert kwargs.get("port") == 0
        assert kwargs.get("prompt") == "consent"
        assert kwargs.get("access_type") == "offline"
        
        # Verify token.json was written
        assert fake_token.exists()
        assert fake_token.read_text() == '{"token": "newly_authorized_token"}'
        assert creds == mock_creds


def test_get_youtube_client():
    """Verify build is called with youtube v3 and OAuth credentials."""
    from src.pipeline import auth
    
    mock_creds = MagicMock()
    with patch("src.pipeline.auth.get_credentials", return_value=mock_creds):
        with patch("src.pipeline.auth.build") as mock_build:
            client = auth.get_youtube_client()
            mock_build.assert_called_once_with("youtube", "v3", credentials=mock_creds)


def test_get_authenticated_channel_id():
    """Verify authenticated channel ID retrieval and caching."""
    from src.pipeline import auth
    auth._cached_channel_id = None
    
    mock_client = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {
        "items": [{"id": "UC_test_authenticated_channel_123", "snippet": {"title": "Test Channel"}}]
    }
    mock_client.channels.return_value.list.return_value = mock_list
    
    channel_id = auth.get_authenticated_channel_id(mock_client)
    assert channel_id == "UC_test_authenticated_channel_123"
    assert auth._cached_channel_id == "UC_test_authenticated_channel_123"
    
    # Second call should return cached ID without invoking client
    mock_client.reset_mock()
    cached_id = auth.get_authenticated_channel_id()
    assert cached_id == "UC_test_authenticated_channel_123"
    mock_client.channels.assert_not_called()

