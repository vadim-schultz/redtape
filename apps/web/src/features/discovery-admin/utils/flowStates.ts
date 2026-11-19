import type { IconType } from "react-icons";
import {
  FaCheckCircle,
  FaClock,
  FaHourglassEnd,
  FaLayerGroup,
  FaLock,
  FaPause,
  FaSkull,
  FaTachometerAlt,
  FaWallet,
} from "react-icons/fa";

import type { FlowStageState } from "../types";

export interface FlowStateMeta {
  Icon: IconType;
  palette: string;
}

/**
 * The icon and colour of each stage state, in one map. The words come from `discovery_admin.flow.state.<state>`,
 * so a state is always named in text and never by its colour alone.
 */
export const FLOW_STATE_META: Readonly<Record<FlowStageState, FlowStateMeta>> =
  {
    dead: { Icon: FaSkull, palette: "red" },
    budget_stopped: { Icon: FaWallet, palette: "orange" },
    throttled: { Icon: FaTachometerAlt, palette: "yellow" },
    blocked: { Icon: FaLock, palette: "purple" },
    starved: { Icon: FaHourglassEnd, palette: "gray" },
    overdue: { Icon: FaClock, palette: "orange" },
    backlogged: { Icon: FaLayerGroup, palette: "yellow" },
    flowing: { Icon: FaCheckCircle, palette: "green" },
    idle: { Icon: FaPause, palette: "gray" },
  };

/** The translation key of a state's label. */
export function flowStateLabelKey(state: FlowStageState): string {
  return `discovery_admin.flow.state.${state}.label`;
}

/** The translation key of a state's one-line description. */
export function flowStateDescriptionKey(state: FlowStageState): string {
  return `discovery_admin.flow.state.${state}.description`;
}
