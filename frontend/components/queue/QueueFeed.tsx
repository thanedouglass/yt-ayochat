"use client";

import { useState, useEffect } from "react";
import { CommentCard } from "./CommentCard";
import { api, HITLQueueItem } from "@/lib/api";
import { RefreshCw, Home, Clock } from "lucide-react";
import { M3Button } from "@/components/ui/M3Button";
import { GlassBottomSheet } from "@/components/ui/GlassBottomSheet";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";

export function QueueFeed() {
  const [queue, setQueue] = useState<HITLQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editingItem, setEditingItem] = useState<HITLQueueItem | null>(null);
  const [editedText, setEditedText] = useState("");
  const [processing, setProcessing] = useState(false);

  const fetchQueue = async () => {
    try {
      const data = await api.getQueue(20);
      setQueue(data);
    } catch (error) {
      console.error("Failed to fetch queue:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    // Poll every 30 seconds
    const interval = setInterval(fetchQueue, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchQueue();
  };

  const handleApprove = async (item: HITLQueueItem) => {
    setProcessing(true);
    try {
      await api.resolveComment({
        record_id: item.id,
        action: "approve",
        notes: "Approved via Mobile PWA"
      });
      // Remove from queue
      setQueue(queue.filter(i => i.id !== item.id));
    } catch (error) {
      console.error("Failed to approve:", error);
      alert("Failed to approve comment");
    } finally {
      setProcessing(false);
    }
  };

  const handleSkip = async (item: HITLQueueItem) => {
    setProcessing(true);
    try {
      await api.resolveComment({
        record_id: item.id,
        action: "skip",
        notes: "Skipped via Mobile PWA"
      });
      setQueue(queue.filter(i => i.id !== item.id));
    } catch (error) {
      console.error("Failed to skip:", error);
      alert("Failed to skip comment");
    } finally {
      setProcessing(false);
    }
  };

  const handleEdit = (item: HITLQueueItem) => {
    setEditingItem(item);
    setEditedText(item.model_draft_reply);
  };

  const handleSaveEdit = async () => {
    if (!editingItem) return;
    
    setProcessing(true);
    try {
      await api.resolveComment({
        record_id: editingItem.id,
        action: "edit",
        edited_reply: editedText,
        notes: "Edited via Mobile PWA"
      });
      setQueue(queue.filter(i => i.id !== editingItem.id));
      setEditingItem(null);
      setEditedText("");
    } catch (error) {
      console.error("Failed to edit:", error);
      alert("Failed to edit comment");
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#030407]">
        <div className="text-center">
          <Clock className="w-12 h-12 text-[var(--m3-primary)] animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030407] pb-20">
      {/* Header */}
      <div className="sticky top-0 z-10 glass-effect border-b border-white/10 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => (window.location.href = "/")}
              className="p-2 rounded-full hover:bg-white/10 transition-colors"
            >
              <Home className="w-5 h-5 text-gray-300" />
            </button>
            <div>
              <h1 className="text-white font-semibold">HITL Queue</h1>
              <p className="text-gray-400 text-xs">{queue.length} pending</p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-5 h-5 text-gray-300", refreshing && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Queue */}
      <div className="px-4 py-4">
        {queue.length === 0 ? (
          <GlassCard className="text-center py-12">
            <Clock className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <h3 className="text-white font-medium mb-2">Queue Empty</h3>
            <p className="text-gray-400 text-sm">No comments pending approval</p>
          </GlassCard>
        ) : (
          queue.map((item) => (
            <CommentCard
              key={item.id}
              item={item}
              onApprove={() => handleApprove(item)}
              onSkip={() => handleSkip(item)}
              onEdit={() => handleEdit(item)}
            />
          ))
        )}
      </div>

      {/* Edit Bottom Sheet */}
      <GlassBottomSheet
        isOpen={!!editingItem}
        onClose={() => {
          setEditingItem(null);
          setEditedText("");
        }}
        title="Edit Reply"
      >
        {editingItem && (
          <div className="space-y-4">
            <div className="glass-effect rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-2">Original Comment</p>
              <p className="text-white text-sm">"{editingItem.input_comment}"</p>
            </div>
            
            <div>
              <label className="text-sm text-gray-300 mb-2 block">Your Reply</label>
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="w-full glass-effect rounded-lg p-3 text-white text-sm min-h-[120px] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--m3-primary)]"
                placeholder="Type your edited reply..."
              />
            </div>

            <div className="flex gap-3">
              <M3Button
                variant="outlined"
                onClick={() => {
                  setEditingItem(null);
                  setEditedText("");
                }}
                className="flex-1"
              >
                Cancel
              </M3Button>
              <M3Button
                onClick={handleSaveEdit}
                disabled={processing || !editedText.trim()}
                className="flex-1"
              >
                {processing ? "Saving..." : "Save & Dispatch"}
              </M3Button>
            </div>
          </div>
        )}
      </GlassBottomSheet>
    </div>
  );
}