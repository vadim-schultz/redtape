import type { KeyboardEvent, MouseEvent } from "react";
import { useNavigate } from "react-router-dom";

const INTERACTIVE = "a,button,input,select,textarea,[role='button']";

/** True when the event came from a control nested inside the row. */
export function isNestedControl(event: MouseEvent | KeyboardEvent): boolean {
  const target = event.target as Element;
  return target.closest(INTERACTIVE) !== null;
}

export interface RowNavigationProps {
  tabIndex?: 0;
  cursor?: "pointer";
  onClick?: (event: MouseEvent) => void;
  onKeyDown?: (event: KeyboardEvent) => void;
}

/** Row props that navigate to `href` without swallowing nested controls. */
export function useRowNavigation(href: string | undefined): RowNavigationProps {
  const navigate = useNavigate();
  if (href === undefined) return {};

  return {
    tabIndex: 0,
    cursor: "pointer",
    onClick: (event) => {
      if (!isNestedControl(event)) void navigate(href);
    },
    onKeyDown: (event) => {
      if (event.key === "Enter" && event.target === event.currentTarget) {
        void navigate(href);
      }
    },
  };
}
