import { Menu, Portal, Skeleton } from "@chakra-ui/react";

import { useLocale } from "../../contexts/LocaleContext";
import { useLocalesQuery } from "./useLocalesQuery";

/** Language picker for the burger menu: a nested menu with the active locale checked. */
export default function LocaleSubmenu() {
  const { locale, setLocale, t } = useLocale();
  const { data: locales, isLoading, error } = useLocalesQuery();

  if (isLoading) {
    return (
      <Skeleton
        role="status"
        aria-label={t("common.loading")}
        height="8"
        borderRadius="md"
      />
    );
  }
  // Switching language is optional; a failed list should not put an error in the menu.
  if (error) return null;

  const enabled = locales?.filter((l) => l.enabled) ?? [];
  const current = enabled.find((l) => l.code === locale);

  return (
    <Menu.Root positioning={{ placement: "right-start", gutter: 2 }}>
      <Menu.TriggerItem>
        {t("common.language")} {current?.flag_emoji ?? "🌐"}
      </Menu.TriggerItem>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            <Menu.RadioItemGroup
              value={locale}
              onValueChange={({ value }) => setLocale(value)}
            >
              {enabled.map((l) => (
                <Menu.RadioItem key={l.code} value={l.code}>
                  {l.flag_emoji} {l.name_native}
                  <Menu.ItemIndicator />
                </Menu.RadioItem>
              ))}
            </Menu.RadioItemGroup>
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
  );
}
