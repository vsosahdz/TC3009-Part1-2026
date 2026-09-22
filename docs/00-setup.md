# Setup — hazlo antes de la sesión 1

Buenas noticias: **tu laptop casi no necesita nada.**

No vas a instalar Python, ni Node, ni Docker. Todo eso vive en una máquina Ubuntu en la nube
que vas a crear en la primera sesión. Tu computadora sólo sirve para escribir código y
empujarlo a GitHub.

```
   Tu laptop              GitHub              Tu instancia EC2
   ─────────────          ──────              ────────────────
   VS Code + git   ─push──▶  tu fork  ─pull──▶  Ubuntu
   escribir                                     ahí corre todo
                                     ◀── terminal desde el navegador
```

Eso significa que da exactamente igual si usas Windows o Mac. Es a propósito.

Esto toma unos 15 minutos.

---

## 1. En tu laptop

| Qué | Dónde | Para qué |
| --- | ----- | -------- |
| **git** | [git-scm.com](https://git-scm.com/downloads) | mover tu código a GitHub |
| **VS Code** | [code.visualstudio.com](https://code.visualstudio.com/) | escribir el código |
| **Cuenta de GitHub** | [github.com](https://github.com/) | donde vive tu repositorio |

En macOS, `git` también llega con `xcode-select --install`.

Configura tu identidad de git una sola vez:

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@tec.mx"
```

---

## 1b. Si usas Windows: pon Git Bash como terminal de VS Code

**Este paso no es opcional y toma dos minutos.** Sáltatelo y la mitad de los comandos del
curso te van a fallar.

VS Code en Windows abre **PowerShell**, y los comandos de este curso están escritos para
`bash` — el mismo intérprete que usan macOS, Linux y tu instancia EC2.

En PowerShell, `./setup/run` falla así:

```
Error al ejecutar el programa 'run': La operación que se ha intentado no está permitida
```

Es el comando con el que arrancas los servidores, traes el material de cada sesión y reparas
tu repositorio. Sin bash, no tienes ninguno de los tres.

La buena noticia: **ya tienes bash**. El instalador de Git para Windows incluye **Git Bash**.
Solo hay que decirle a VS Code que lo use.

1. Abre VS Code.
2. `Ctrl+Shift+P` → escribe **Terminal: Select Default Profile**.
3. Elige **Git Bash**.
4. Cierra la terminal que tengas abierta (el icono del bote de basura) y abre una nueva con
   `` Ctrl+Ñ `` (o **Terminal → New Terminal**).

Compruébalo. En la terminal nueva:

```bash
echo $SHELL
```

Tiene que responder algo que termine en `bash`. Si no dice nada, o dice algo con
`powershell`, todavía estás en PowerShell y los comandos te van a fallar.

A partir de ahí, **los comandos del curso son idénticos en Windows y en Mac**. No hay una
versión para cada uno, y eso es a propósito: con dos juegos de instrucciones, la mitad de la
clase acaba corriendo la que no era.

> **Un detalle que ya está resuelto.** El instalador de Git para Windows trae
> `core.autocrlf=true`, que convierte los archivos a finales de línea de Windows al clonar.
> Git Bash los tolera, pero otras herramientas no, y en algunos sistemas el síntoma es un
> mensaje que no explica nada: `env: bash\r: No such file or directory`.
>
> Este repositorio trae un `.gitattributes` que fuerza finales de línea de Unix, así que
> **no tienes que configurar nada**. Si ves ese mensaje en otro proyecto, ya sabes qué es.

---

## 2. Haz fork del repositorio

Entra a **<https://github.com/vsosahdz/TC3009-Part1-2026>** y presiona **Fork**.

Eso te crea tu propia copia. Vas a trabajar sobre ella toda la concentración, y es la que
vas a clonar en tu instancia.

Déjala **pública**: en la sesión 1 la vas a clonar desde una máquina en la nube que no tiene
tus credenciales de GitHub.

Ahora clónala en tu laptop y ábrela en VS Code:

```bash
git clone https://github.com/TU-USUARIO/TC3009-Part1-2026.git
cd TC3009-Part1-2026
code .
```

---

## 3. Verifica que todo está en su lugar

Marca las cuatro casillas antes de llegar a clase:

- [ ] `git --version` responde algo
- [ ] `git config --global user.name` muestra tu nombre
- [ ] Hiciste fork y lo clonaste; VS Code abre la carpeta y ves `README.md`
- [ ] `git tag` muestra `s1`, `s2`, `s3` y `s4`
- [ ] **En Windows:** `echo $SHELL` en la terminal de VS Code termina en `bash`

La última es la que más gente omite y la que más caro sale. Si en Windows te responde vacío o
algo con `powershell`, vuelve al paso 1b: no es un detalle cosmético, es que los comandos del
curso no van a correr.

Si `git tag` no muestra los cuatro, avisa antes de la sesión — significa que tu fork se hizo
antes de tiempo y el mecanismo de recuperación no te va a funcionar.

---

## 4. Confirma que entras al laboratorio de AWS

Entra a **AWS Academy Learner Lab**, presiona **Start Lab**, espera el punto verde y abre la
consola de AWS.

No crees nada todavía — eso es lo primero que hacemos juntos en la sesión 1. Sólo confirma
que entras y que tienes presupuesto disponible. Si el laboratorio no te abre, resuélvelo
antes de la clase.

**Presiona End Lab** cuando termines de comprobarlo.

---

## Cómo va a ser el ciclo de trabajo

Vale la pena entenderlo desde ahora, porque es distinto a lo que estás acostumbrado:

```
   1. Editas en VS Code, en tu laptop
   2. git add · git commit · git push
   3. En la terminal de tu instancia:  sync
   4. Reinicias los servidores y recargas el navegador
```

Tu código **viaja** hasta donde se ejecuta. No es una molestia del curso: es exactamente lo
que pasa en cualquier producto real, y es más fácil acostumbrarse ahora que descubrirlo
después.

---

## Problemas comunes

**`git` no se reconoce como comando en Windows.**
Reinstala desde git-scm.com y reinicia la terminal. El instalador agrega git al PATH, pero
las terminales ya abiertas conservan el PATH viejo.

**Windows: `Error al ejecutar el programa 'run': La operación que se ha intentado no está permitida`.**
Estás en PowerShell. Es el error más común del curso en Windows y solo tiene una causa. Ve al
paso 1b y pon Git Bash como terminal de VS Code.

**Windows: `env: bash\r: No such file or directory`.**
Finales de línea de Windows en un script. No debería pasarte —el repositorio trae un
`.gitattributes` que lo impide— pero si clonaste antes de que existiera, vuelve a clonar:

```bash
cd ..
rm -rf TC3009-Part1-2026
git clone https://github.com/TU-USUARIO/TC3009-Part1-2026.git
```

**Hice fork pero `git tag` no muestra nada.**
Un fork se lleva los tags que existían al momento de hacerlo. Si los tuyo no los tiene, el
repositorio del curso todavía no los tenía cuando forkeaste. Avisa.

**No tengo cuenta de GitHub con mi correo del Tec.**
No hace falta que sea el del Tec. Cualquier cuenta sirve.

**¿No necesito Python de verdad?**
De verdad. Si ya lo tienes instalado no estorba, pero no lo vamos a usar en tu laptop.
