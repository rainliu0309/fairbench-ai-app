import { useMutation, useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { authApi } from "../../api/endpoints";
import { LanguageSwitcher } from "../../components/common/LanguageSwitcher";
import { sessionStore } from "../../store/session";
import { useTranslation } from "react-i18next";

export function Auth() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setup = useQuery({ queryKey: ["auth", "setup"], queryFn: authApi.setupStatus, retry: false });
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const isSetup = Boolean(setup.data?.setup_required);
  const demoLoginAvailable = !isSetup && Boolean(setup.data?.demo_login_available);
  useEffect(() => {
    if (setup.data?.default_admin_email) setEmail(setup.data.default_admin_email);
  }, [setup.data?.default_admin_email]);
  const authenticate = useMutation({
    mutationFn: () =>
      isSetup
        ? authApi.bootstrap({ email, display_name: displayName, password })
        : authApi.login({ email, password }),
    onSuccess: (result) => {
      sessionStore.setAuth(result.access_token, result.user);
      navigate("/datasets", { replace: true });
    },
  });
  const demoLogin = useMutation({
    mutationFn: authApi.localSession,
    onSuccess: (result) => {
      sessionStore.setAuth(result.access_token, result.user);
      navigate("/datasets", { replace: true });
    },
  });

  if (sessionStore.getToken()) return <Navigate to="/datasets" replace />;
  const valid = email.includes("@") && password.length >= (isSetup ? 12 : 1) && (!isSetup || (displayName.trim().length >= 2 && password === confirmPassword));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (valid) authenticate.mutate();
  };

  return (
    <main className="auth-shell">
      <section className={`auth-card${demoLoginAvailable ? " auth-card-demo" : ""}`}>
        <div className="auth-seal">FB</div>
        {demoLoginAvailable ? (
          <div className="auth-demo">
            <h1>Fair Bench</h1>
            <p className="auth-demo-subtitle">{t("auth.demoWorkspace")}</p>
            <div className="auth-form">
              <label>
                <span>{t("auth.demoAdministrator")}</span>
                <input
                  type="email"
                  value={email}
                  readOnly
                  aria-readonly="true"
                />
              </label>
              <button
                className="button auth-submit"
                disabled={demoLogin.isPending}
                type="button"
                onClick={() => demoLogin.mutate()}
              >
                <ShieldCheck />
                {t("auth.signIn")}
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="auth-eyebrow">{t("auth.eyebrow")}</div>
            <h1>{isSetup ? t("auth.setupTitle") : t("auth.loginTitle")}</h1>
            <p>{isSetup ? t("auth.setupDescription") : t("auth.loginDescription")}</p>
            <form className="auth-form" onSubmit={submit}>
              {isSetup ? <label><span>{t("auth.displayName")}</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="name" /></label> : null}
              <label><span>{t("auth.email")}</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
              <label><span>{t("auth.password")}</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={isSetup ? "new-password" : "current-password"} /></label>
              {isSetup ? <label><span>{t("auth.confirmPassword")}</span><input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" /></label> : null}
              {isSetup ? <div className="auth-hint">{t("auth.passwordHint")}</div> : null}
              <button className="button auth-submit" disabled={!valid || authenticate.isPending} type="submit"><ShieldCheck />{isSetup ? t("auth.createAccount") : t("auth.signIn")}</button>
            </form>
          </>
        )}
      </section>
      <div className="auth-language-switcher"><LanguageSwitcher /></div>
    </main>
  );
}
