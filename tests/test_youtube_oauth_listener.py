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
