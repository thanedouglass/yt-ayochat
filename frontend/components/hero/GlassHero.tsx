"use client";

import { M3Button } from "@/components/ui/M3Button";
import { ArrowRight, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

export function GlassHero() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100,
      });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-[#030407]">
      {/* Animated Background */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background: `radial-gradient(circle at ${mousePosition.x}% ${mousePosition.y}%, 
            rgba(99, 102, 241, 0.15) 0%, 
            rgba(15, 23, 42, 0.5) 50%, 
            transparent 100%)`,
          transition: "background 0.3s ease-out",
        }}
      />

      {/* Grid Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(99, 102, 241, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99, 102, 241, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: "50px 50px",
        }} />
      </div>

      {/* Floating Glass Shards */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute glass-effect rounded-lg opacity-20"
            style={{
              width: `${Math.random() * 200 + 100}px`,
              height: `${Math.random() * 200 + 100}px`,
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              transform: `rotate(${Math.random() * 360}deg)`,
              animation: `float ${Math.random() * 10 + 10}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <div className="relative z-10 text-center px-6 max-w-2xl mx-auto">
        {/* Logo/Brand */}
        <div className="mb-8 flex justify-center">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl glass-effect flex items-center justify-center luminescent-glow">
              <Sparkles className="w-10 h-10 text-[var(--m3-primary)]" />
            </div>
            <div className="absolute -inset-2 rounded-2xl bg-[var(--m3-primary)] opacity-20 blur-xl animate-pulse-slow" />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-5xl md:text-7xl font-bold mb-4 bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
          AyoChat
        </h1>

        {/* Subtitle */}
        <p className="text-xl md:text-2xl text-gray-300 mb-2 font-light">
          Mobile Companion
        </p>

        {/* Description */}
        <p className="text-gray-400 mb-8 max-w-md mx-auto leading-relaxed">
          AI-powered Human-in-the-Loop moderation for YouTube creators. 
          Break through the algorithmic black box.
        </p>

        {/* CTA Button */}
        <div className="flex justify-center">
          <M3Button
            size="large"
            onClick={() => (window.location.href = "/queue")}
            className="gap-2"
          >
            Enter Dashboard
            <ArrowRight className="w-5 h-5" />
          </M3Button>
        </div>

        {/* Feature Pills */}
        <div className="mt-12 flex flex-wrap justify-center gap-3">
          {[
            "AI-Powered",
            "Mobile-First",
            "Real-Time",
            "Vector-Aligned"
          ].map((feature) => (
            <div
              key={feature}
              className="glass-effect px-4 py-2 rounded-full text-sm text-gray-300"
            >
              {feature}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Gradient */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#030407] to-transparent pointer-events-none" />

      <style jsx>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0) rotate(0deg);
          }
          50% {
            transform: translateY(-20px) rotate(5deg);
          }
        }
      `}</style>
    </div>
  );
}