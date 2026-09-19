"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import type { Moment } from "@/types/moment";

function FallbackField({ moment }: { moment: Moment }) {
  const tone =
    moment.eventType === "surprise"
      ? "from-[#2a2114] via-[#12110f] to-black"
      : moment.eventType === "insight"
        ? "from-[#182028] via-[#101215] to-black"
        : moment.eventType === "load"
        ? "from-[#1f1a26] via-[#131117] to-black"
        : "from-[#261816] via-[#141110] to-black";

  return (
    <div className={cn("absolute inset-0 bg-gradient-to-br", tone)}>
      <div className="absolute inset-0 opacity-40 [background-image:radial-gradient(circle_at_20%_20%,rgba(243,239,230,0.12),transparent_42%),radial-gradient(circle_at_80%_70%,rgba(201,184,150,0.1),transparent_38%)]" />
    </div>
  );
}

function MomentVisual({
  moment,
  active,
  autoplay,
}: {
  moment: Moment;
  active: boolean;
  autoplay: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const [videoFailed, setVideoFailed] = useState(!moment.media.videoUrl);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || videoFailed) return;
    if (active && autoplay) {
      const play = video.play();
      if (play) play.catch(() => undefined);
    } else {
      video.pause();
    }
  }, [active, autoplay, videoFailed, moment.id]);

  return (
    <div className="absolute inset-0">
      {imageFailed ? <FallbackField moment={moment} /> : null}
      {!imageFailed ? (
        // Native img keeps remote placeholders simple and avoids next/image domain config.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={moment.media.thumbnailUrl}
          alt=""
          className={cn(
            "absolute inset-0 h-full w-full object-cover",
            !videoReady && "kenburns",
          )}
          onError={() => setImageFailed(true)}
        />
      ) : null}
      {moment.media.videoUrl && !videoFailed ? (
        <video
          ref={videoRef}
          muted
          loop
          playsInline
          preload="metadata"
          poster={moment.media.thumbnailUrl}
          className={cn(
            "absolute inset-0 h-full w-full object-cover transition-opacity duration-700",
            videoReady ? "opacity-100" : "opacity-0",
          )}
          onError={() => setVideoFailed(true)}
          onPlaying={() => setVideoReady(true)}
        >
          <source src={moment.media.videoUrl} type="video/mp4" />
        </video>
      ) : null}
    </div>
  );
}

export function MediaBackdrop({
  moment,
  autoplay = true,
  className,
}: {
  moment: Moment;
  autoplay?: boolean;
  className?: string;
}) {
  const [front, setFront] = useState(moment);
  const [back, setBack] = useState(moment);
  const [showFront, setShowFront] = useState(true);

  const visible = showFront ? front : back;
  if (moment.id !== visible.id) {
    if (showFront) {
      setBack(moment);
      setShowFront(false);
    } else {
      setFront(moment);
      setShowFront(true);
    }
  }

  return (
    <div className={cn("absolute inset-0 overflow-hidden bg-black", className)}>
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-700 ease-out",
          showFront ? "opacity-100" : "opacity-0",
        )}
      >
        <MomentVisual moment={front} active={showFront} autoplay={autoplay} />
      </div>
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-700 ease-out",
          showFront ? "opacity-0" : "opacity-100",
        )}
      >
        <MomentVisual moment={back} active={!showFront} autoplay={autoplay} />
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/55 to-black/50" />
      <div className="absolute inset-0 bg-gradient-to-r from-bg/80 via-bg/25 to-transparent" />
      <div className="grain absolute inset-0" />
    </div>
  );
}
