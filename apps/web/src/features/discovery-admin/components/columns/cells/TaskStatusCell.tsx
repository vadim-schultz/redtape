import type { DiscoveryTask } from "../../../types";
import TaskResultNote from "../../TaskResultNote";

/** A task's status followed by its result note, when it has one. */
export default function TaskStatusCell({ task }: { task: DiscoveryTask }) {
  return (
    <>
      {task.status}
      {task.result_note ? <TaskResultNote note={task.result_note} /> : null}
    </>
  );
}
