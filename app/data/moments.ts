import type { Moment } from "@/types/moment";

/**
 * Deliberately empty.
 *
 * This held hand-written demo moments with timestamps anchored to the current day. They
 * were indistinguishable from real captures in the UI while being entirely invented, and
 * because they were anchored to the afternoon they outranked clips actually recorded that
 * morning. Every moment the interface shows now comes from the backend: a real recording,
 * stopped by the detector and uploaded from the phone.
 *
 * If the backend is not running the interface is empty, and that is the honest state.
 */
export const INITIAL_MOMENTS: Moment[] = [];
