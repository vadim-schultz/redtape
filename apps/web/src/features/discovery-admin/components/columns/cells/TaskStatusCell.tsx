import { useLocale } from "../../../../../contexts/LocaleContext";
import type { DiscoveryTask } from "../../../types";
import { translateOrRaw } from "../../../utils/translateOrRaw";
import TaskResultNote from "../../TaskResultNote";

/** A task's status followed by its result note, when it has one. */
export default function TaskStatusCell({ task }: { task: DiscoveryTask }) {
  const { t } = useLocale();
  const label = translateOrRaw(
    t,
    `discovery_admin.values.task_status_${task.status}`,
    task.status,
  );

  return (
    <>
      {label}
      {task.result_note ? <TaskResultNote note={task.result_note} /> : null}
    </>
  );
}
