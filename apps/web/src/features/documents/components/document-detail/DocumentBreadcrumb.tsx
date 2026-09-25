import { Fragment } from "react";
import { Breadcrumb } from "@chakra-ui/react";

import type { JurisdictionPathNode } from "../../types";

export interface DocumentBreadcrumbProps {
  nodes: JurisdictionPathNode[];
}

export default function DocumentBreadcrumb({ nodes }: DocumentBreadcrumbProps) {
  if (!nodes.length) {
    return null;
  }

  const lastIndex = nodes.length - 1;

  return (
    <Breadcrumb.Root>
      <Breadcrumb.List>
        {nodes.map((node, index) => (
          <Fragment key={node.code}>
            <Breadcrumb.Item>
              {index === lastIndex ? (
                <Breadcrumb.CurrentLink>{node.name}</Breadcrumb.CurrentLink>
              ) : (
                <Breadcrumb.Link>{node.name}</Breadcrumb.Link>
              )}
            </Breadcrumb.Item>
            {index < lastIndex ? <Breadcrumb.Separator /> : null}
          </Fragment>
        ))}
      </Breadcrumb.List>
    </Breadcrumb.Root>
  );
}
