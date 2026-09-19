"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { INITIAL_MOMENTS } from "@/data/moments";
import { loadMoments, persistMoment } from "@/lib/integrations";
import type { Moment } from "@/types/moment";

const CAPTURE_POLL_MS = 5000;

interface MomentsContextValue {
  moments: Moment[];
  visibleMoments: Moment[];
  lastCreatedId: string | null;
  getMoment: (id: string) => Moment | undefined;
  addMoment: (moment: Moment) => void;
  updateMoment: (id: string, patch: Partial<Moment>) => void;
  keepMoment: (id: string) => void;
  deleteMoment: (id: string) => void;
  nextSequence: () => number;
}

const MomentsContext = createContext<MomentsContextValue | null>(null);

const isCapture = (moment: Moment) => moment.id.startsWith("capture-");

/**
 * Real captures first, then seed moments, each newest-first. Without this a clip
 * recorded this morning sorts below demo data anchored to this afternoon, so the thing
 * the hardware just produced never reaches the hero slot.
 */
function sortMoments(moments: Moment[]): Moment[] {
  return [...moments].sort((a, b) => {
    if (isCapture(a) !== isCapture(b)) return isCapture(a) ? -1 : 1;
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });
}

export function MomentsProvider({ children }: { children: ReactNode }) {
  const [moments, setMoments] = useState<Moment[]>(() => sortMoments(INITIAL_MOMENTS));
  const [lastCreatedId, setLastCreatedId] = useState<string | null>(null);

  // Real captures arrive from the backend after a recording is stopped and uploaded.
  // They are merged by id alongside the seed moments rather than replacing them, so
  // the demo still has content when no session is running.
  useEffect(() => {
    let cancelled = false;

    const merge = async () => {
      const captured = await loadMoments();
      if (cancelled || !captured?.length) return;
      setMoments((current) => {
        const known = new Set(current.map((moment) => moment.id));
        const fresh = captured.filter((moment) => !known.has(moment.id));
        return fresh.length ? sortMoments([...fresh, ...current]) : current;
      });
    };

    void merge();
    const timer = window.setInterval(merge, CAPTURE_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const value = useMemo<MomentsContextValue>(() => {
    const getMoment = (id: string) => moments.find((moment) => moment.id === id);

    return {
      moments,
      visibleMoments: moments.filter((moment) => moment.status !== "deleted"),
      lastCreatedId,
      getMoment,
      addMoment: (moment) => {
        setMoments((current) => sortMoments([moment, ...current]));
        setLastCreatedId(moment.id);
        void persistMoment(moment);
      },
      updateMoment: (id, patch) => {
        setMoments((current) =>
          sortMoments(
            current.map((moment) =>
              moment.id === id ? { ...moment, ...patch } : moment,
            ),
          ),
        );
      },
      keepMoment: (id) => {
        setMoments((current) =>
          current.map((moment) =>
            moment.id === id ? { ...moment, status: "kept" } : moment,
          ),
        );
      },
      deleteMoment: (id) => {
        setMoments((current) =>
          current.map((moment) =>
            moment.id === id ? { ...moment, status: "deleted" } : moment,
          ),
        );
      },
      nextSequence: () =>
        moments.reduce((max, moment) => Math.max(max, moment.sequence), 0) + 1,
    };
  }, [lastCreatedId, moments]);

  return (
    <MomentsContext.Provider value={value}>{children}</MomentsContext.Provider>
  );
}

export function useMoments(): MomentsContextValue {
  const context = useContext(MomentsContext);
  if (!context) {
    throw new Error("useMoments must be used within MomentsProvider");
  }
  return context;
}
