# Как отправить коммиты на GitHub, если `git push` не работает

На сервере репозиторий **уже закоммичен** (ветка `master` впереди `origin/master` на 2 коммита).  
`git push` с сервера падает, потому что нет логина GitHub (HTTPS без токена).

Репозиторий: https://github.com/ocean1nside/Orchestra-of-AI-agents

---

## Способ 1 — с вашего компьютера (рекомендуется)

1. Откройте терминал в папке, где уже есть клон репозитория (или клонируйте заново).
2. Подтяните изменения **с сервера по SSH** (подставьте свой хост и путь):

```bash
ssh user@ВАШ-СЕРВЕР "cd /opt/orchestra/Orchestra-of-AI-agents && git log -3 --oneline"
```

3. Скопируйте bundle с сервера и примените локально:

```bash
scp user@ВАШ-СЕРВЕР:/tmp/orchestra-push.bundle .
git pull orchestra-push.bundle master
git push origin master
```

Если локальный `master` уже совпадает с GitHub до старых коммитов, после `git pull orchestra-push.bundle master` появятся 2 новых коммита, затем обычный `git push`.

---

## Способ 2 — Personal Access Token (HTTPS)

1. GitHub → Settings → Developer settings → Personal access tokens → Generate (scope **repo**).
2. На **своём ПК** в каталоге клона:

```bash
git remote set-url origin https://ВАШ_ЛОГИН_GITHUB@github.com/ocean1nside/Orchestra-of-AI-agents.git
# при push GitHub запросит пароль — вставьте ТОКЕН, не пароль от аккаунта
git push origin master
```

Или один раз без сохранения в URL:

```bash
git push https://ВАШ_ЛОГИН:ВАШ_ТОКЕН@github.com/ocean1nside/Orchestra-of-AI-agents.git master
```

На сервере так же можно, если **вы** выполните команду с токеном (не передавайте токен в чаты).

---

## Способ 3 — SSH-ключ на сервере

На сервере:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_orchestra -N ""
cat ~/.ssh/github_orchestra.pub
```

Скопируйте вывод → GitHub → репозиторий → Settings → Deploy keys → Add (Allow write).

```bash
cd /opt/orchestra/Orchestra-of-AI-agents
git remote set-url origin git@github.com:ocean1nside/Orchestra-of-AI-agents.git
GIT_SSH_COMMAND='ssh -i ~/.ssh/github_orchestra -o IdentitiesOnly=yes' git push origin master
```

---

## Что уже запущено на сервере (Docker)

```bash
cd /opt/orchestra/Orchestra-of-AI-agents/infra
docker compose -f docker-compose.dev.yml ps
```

Ожидаются: postgres, redis, qdrant, orchestrator-api (:8000), vendor-support-agent (:8010), indexing-worker, test-ui-studio (:8790, profile devtools).

Studio: https://212-67-10-140.sslip.io/studio/ (Basic Auth из корневого `.env`).
