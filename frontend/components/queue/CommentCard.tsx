"use client";

import { GlassCard } from "@/components/ui/GlassCard";
import { Shield, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { HITLQueueItem } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CommentCardProps {
  item: HITLQueueItem;
  onApprove: () => void;
  onSkip: () => void;
  onEdit: () => void;
  disabled?: boolean;
  className?: string;
}

export function CommentCard({ item, onApprove, onSkip, onEdit, disabled = false, className }: CommentCardProps) {
  const isSafe = item.cultural_alignment_flag;
  
  return (
    <GlassCard className={cn("p-4 mb-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--m3-primary)] to-[var(--m3-tertiary)] flex items-center justify-center text-white text-sm font-bold">
            {item.author_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-white font-medium text-sm">{item.author_name}</p>
            <p className="text-gray-400 text-xs">{item.video_title}</p>
          </div>
        </div>
        <div className={cn(
          "flex items-center gap-1 px-2 py-1 rounded-full text-xs",
          isSafe ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
        )}>
          {isSafe ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <AlertTriangle className="w-3 h-3" />
          )}
          <span>{isSafe ? "Safe" : "Toxic"}</span>
        </div>
      </div>

      {/* Comment */}
      <div className="mb-3">
        <p className="text-gray-300 text-sm leading-relaxed">
          "{item.input_comment}"
        </p>
      </div>

      {/* Perception */}
      <div className="flex items-center gap-2 mb-3 text-xs text-gray-400">
        <span className="px-2 py-1 rounded bg-white/5">{item.category}</span>
        <span>•</span>
        <span>{item.semiotic_intent}</span>
        <span>•</span>
        <span>Energy: {item.energy_level}/5</span>
      </div>

      {/* Model Draft */}
      <div className="glass-effect rounded-lg p-3 mb-3">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-4 h-4 text-[var(--m3-primary)]" />
          <span className="text-xs text-gray-400 font-medium">Gemini 3.7 Flash Draft</span>
        </div>
        <p className="text-white text-sm leading-relaxed">
          {item.model_draft_reply}
        </p>
      </div>

      {/* Vectors */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="glass-effect rounded p-2">
          <p className="text-xs text-gray-400 mb-1">α_cs (Code-Switch)</p>
          <p className="text-white text-sm font-mono">{item.applied_vectors.code_switch_alpha.toFixed(2)}</p>
        </div>
        <div className="glass-effect rounded p-2">
          <p className="text-xs text-gray-400 mb-1">β_sf (Sovereignty)</p>
          <p className="text-white text-sm font-mono">{item.applied_vectors.sovereignty_beta}</p>
        </div>
        <div className="glass-effect rounded p-2">
          <p className="text-xs text-gray-400 mb-1">γ_fr (Frequency)</p>
          <p className="text-white text-sm font-mono">{item.applied_vectors.frequency_gamma}/5</p>
        </div>
        <div className="glass-effect rounded p-2">
          <p className="text-xs text-gray-400 mb-1">τ_max (Token)</p>
          <p className="text-white text-sm font-mono">{item.applied_vectors.token_economy_tau}</p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          disabled={disabled}
          className="flex-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 py-2 px-3 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Approve
        </button>
        <button
          onClick={onSkip}
          disabled={disabled}
          className="flex-1 bg-gray-500/20 hover:bg-gray-500/30 text-gray-400 py-2 px-3 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Skip
        </button>
        <button
          onClick={onEdit}
          disabled={disabled}
          className="flex-1 bg-[var(--m3-primary)]/20 hover:bg-[var(--m3-primary)]/30 text-[var(--m3-primary)] py-2 px-3 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Edit
        </button>
      </div>
    </GlassCard>
  );
}