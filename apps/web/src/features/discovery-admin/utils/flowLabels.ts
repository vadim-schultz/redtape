import type { FlowResource, FlowStage } from "../types";
import { translateOrRaw } from "./translateOrRaw";

type Translate = (key: string) => string;

/** The translated name of a stage by its id; `fallback` is shown when the bundle has no name for it. */
export function flowStageName(
  id: string,
  t: Translate,
  fallback: string = id,
): string {
  return translateOrRaw(t, `discovery_admin.flow.stage.${id}`, fallback);
}

/** The translated name of a stage record, with the response's own label as the fallback. */
export function flowStageLabel(stage: FlowStage, t: Translate): string {
  return flowStageName(stage.id, t, stage.label);
}

/** The translated name of a run stage (what wrote the spend), with the raw name as the fallback. */
export function flowRunStageLabel(runStage: string, t: Translate): string {
  return translateOrRaw(
    t,
    `discovery_admin.flow.run_stage.${runStage}`,
    runStage,
  );
}

/** The translated name of an allotment's resource, such as "AI neurons". */
export function flowResourceLabel(
  resource: FlowResource,
  t: Translate,
): string {
  return translateOrRaw(
    t,
    `discovery_admin.artifacts.budget_${resource}`,
    resource,
  );
}
