import { Menu } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../contexts/LocaleContext";
import { useAuth } from "../../features/auth/contexts/AuthContext";

/** Sign-in link for anonymous visitors, or the account email and Sign out for authenticated ones. */
export default function AccountMenuItem() {
  const { status, user, session, signOut } = useAuth();
  const { t } = useLocale();

  if (status === "anonymous") {
    return (
      <Menu.Item value="sign-in" asChild>
        <Link to="/login">{t("auth.sign_in")}</Link>
      </Menu.Item>
    );
  }

  if (status !== "authenticated") return null;

  return (
    <Menu.ItemGroup>
      <Menu.ItemGroupLabel>{user?.email ?? session?.email}</Menu.ItemGroupLabel>
      <Menu.Item value="sign-out" onClick={() => void signOut()}>
        {t("auth.sign_out")}
      </Menu.Item>
    </Menu.ItemGroup>
  );
}
