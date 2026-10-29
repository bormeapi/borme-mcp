# Conector MCP de BORME API

[![MCP Badge](https://lobehub.com/badge/mcp/bormeapi-borme-mcp)](https://lobehub.com/mcp/bormeapi-borme-mcp)

*English: [README.md](README.md)*

Conecte Microsoft Copilot, Claude, ChatGPT, Cursor, VS Code o cualquier
cliente MCP al servidor MCP alojado de **BORME API**: datos del Registro
Mercantil publicados en el BORME (Boletín Oficial del Registro Mercantil), con
más de 9,6 millones de eventos desde 2009, historial de sociedades, búsqueda de
sociedades por nombre, búsqueda por NIF, marcas y nombres comerciales, y
señales de riesgo.

El servidor está alojado en `mcp.bormeapi.com`; no tiene que instalar ni
ejecutar nada, y es la forma recomendada de conectarse. Este repositorio reúne
lo necesario a su alrededor: la configuración de cada cliente, una skill para
agentes, el vocabulario de tipos de acto y un servidor stdio local que da
acceso a los endpoints REST de BORME API, para los clientes que solo inician
servidores por stdio.

La guía completa y actualizada está en
[bormeapi.com/es/mcp](https://bormeapi.com/es/mcp). Si este README y esa
página no coinciden, prevalece la página.

## Dos formas de conectarse

**Clave de API: `https://mcp.bormeapi.com/mcp`**

- Transporte: Streamable HTTP. Cada petición recibe una respuesta JSON simple;
  no se mantiene ninguna sesión entre llamadas.
- Autenticación: su clave de API en la cabecera `X-API-Key`. Sin clave, se
  aplican los límites del plan gratuito.
- Para los clientes que pueden enviar una cabecera: Microsoft Copilot Studio,
  Claude Code, Cursor, VS Code, Claude Desktop (mediante mcp-remote) y
  cualquier otro cliente Streamable HTTP.

**OAuth: `https://mcp.bormeapi.com/mcp/oauth`**

- Para los asistentes con conectores personalizados que inician sesión
  mediante OAuth, como Claude.ai, ChatGPT o Copilot. No tiene que pegar
  ninguna clave de API en ningún sitio: inicie sesión con su cuenta de BORME
  API y la aplicación utilizará el plan de la cuenta que la autorizó.
- Esta URL del servidor requiere una cuenta de BORME API e ignora la cabecera
  `X-API-Key`. Sus llamadas comparten la cuota diaria de su clave de API con
  las llamadas a la API REST y a `/mcp` realizadas con esa clave.
- Si su cuenta no tiene ninguna clave de API activa, las herramientas
  devuelven un error que le remite a la página de su cuenta; vuelven a
  funcionar cuando su cuenta tiene una clave activa, sin necesidad de volver a
  conectar la aplicación.
- Si la aplicación no usa la conexión durante 30 días, tendrá que conectarla
  de nuevo. Puede desconectar la aplicación en cualquier momento en el
  apartado «Aplicaciones conectadas» de
  [su cuenta](https://bormeapi.com/es/account).
- Para desarrolladores de clientes: una llamada sin autenticar recibe `401`
  con
  `WWW-Authenticate: Bearer resource_metadata="https://mcp.bormeapi.com/.well-known/oauth-protected-resource/mcp/oauth"`.
  El servidor de autorización es `https://bormeapi.com` (metadatos en
  `/.well-known/oauth-authorization-server`), con registro dinámico de
  clientes, PKCE (`S256`) y el ámbito `mcp`.

Obtenga una clave de API en [su cuenta](https://bormeapi.com/es/account).

## Configure su cliente

### Claude.ai (OAuth)

1. Vaya a Customize > Connectors > Add custom connector.
2. Indique `https://mcp.bormeapi.com/mcp/oauth` como URL del servidor. Claude
   detecta cómo iniciar sesión y muestra Sign in now y Register
   automatically; mantenga esas opciones.
3. Pulse Add. Se abre nuestra página de acceso.
4. Inicie sesión con el enlace que le enviamos por correo electrónico y pulse
   Allow (Permitir, si la página se muestra en español).
5. De vuelta en Claude, si la página del conector indica que no tiene
   herramientas, recargue la página.

En los planes Team y Enterprise, un propietario añade el conector en
Organization settings.

Para usar su clave de API, indique `https://mcp.bormeapi.com/mcp`, elija No
sign-in y añada la cabecera `x-api-key` con su clave en Request headers.
Anthropic ofrece las cabeceras de petición en beta a un número limitado de
organizaciones; si no ve esa sección, use la configuración de Claude Desktop
que figura más abajo.

### ChatGPT (OAuth)

Los conectores personalizados de ChatGPT no pueden enviar una cabecera con la
clave de API. Añada un conector personalizado con
`https://mcp.bormeapi.com/mcp/oauth` como URL del servidor e inicie sesión
con su cuenta de BORME API. Las pantallas y sus nombres pueden ser distintos
de los de Claude.ai. Sin OAuth, ChatGPT solo puede usar
`https://mcp.bormeapi.com/mcp` sin clave, con el plan gratuito.

### Microsoft Copilot Studio y Microsoft 365 Copilot (clave de API)

Estos pasos siguen la documentación de Microsoft. Pueden variar según su
inquilino (tenant) y sus directivas de prevención de pérdida de datos (DLP).

1. En Copilot Studio, abra el agente que vaya a usar y vaya a Herramientas >
   Agregar una herramienta > Nueva herramienta > Protocolo de contexto de
   modelo.
2. Indique el nombre del servidor (BORME API), una descripción y la URL del
   servidor: `https://mcp.bormeapi.com/mcp`
3. En el tipo de autenticación, seleccione Clave de API > Encabezado e
   indique `X-API-Key` como nombre. Pulse Crear; después, Crear una nueva
   conexión, introduzca su clave y seleccione Agregar al agente.
4. Pruebe primero el agente en Copilot Studio. Después, publíquelo y
   configure el canal Teams y Microsoft 365 Copilot, sujeto a los permisos y
   directivas de su organización. Si su organización tiene directivas de
   datos (DLP) en Power Platform, puede que un administrador tenga que
   permitir este conector.

### Claude Code (clave de API)

```bash
claude mcp add --transport http --scope user \
  --header "X-API-Key: SU_CLAVE" \
  borme https://mcp.bormeapi.com/mcp
```

`--scope user` deja el servidor disponible en todos sus proyectos; sin esa
opción, se añade solo al proyecto actual.

### Cursor (clave de API)

Añada esto a `~/.cursor/mcp.json` (todos los proyectos) o a
`.cursor/mcp.json` (un proyecto) y defina `BORME_API_KEY` en su entorno:

```json
{
  "mcpServers": {
    "borme": {
      "url": "https://mcp.bormeapi.com/mcp",
      "headers": { "X-API-Key": "${env:BORME_API_KEY}" }
    }
  }
}
```

### VS Code (clave de API)

Añada esto a `.vscode/mcp.json` en su espacio de trabajo. VS Code le pide la
clave la primera vez que se inicia el servidor:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "borme-api-key",
      "description": "BORME API key",
      "password": true
    }
  ],
  "servers": {
    "borme": {
      "type": "http",
      "url": "https://mcp.bormeapi.com/mcp",
      "headers": { "X-API-Key": "${input:borme-api-key}" }
    }
  }
}
```

### Claude Desktop (clave de API)

Añada el servidor a `claude_desktop_config.json` mediante
[mcp-remote](https://github.com/geelen/mcp-remote), un puente de terceros que
necesita Node.js:

```json
{
  "mcpServers": {
    "borme": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.bormeapi.com/mcp",
               "--header", "X-API-Key:${BORME_API_KEY}"],
      "env": { "BORME_API_KEY": "SU_CLAVE" }
    }
  }
}
```

### Cualquier otro cliente Streamable HTTP (clave de API)

Envíe cada mensaje JSON-RPC con POST a `https://mcp.bormeapi.com/mcp`, con
`Content-Type: application/json`, una cabecera `Accept` que incluya
`application/json` y su clave en `X-API-Key`. Por ejemplo, para obtener la
lista de herramientas:

```bash
curl -s https://mcp.bormeapi.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: SU_CLAVE" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Servidor stdio local

[`server.py`](server.py) es un servidor stdio local que da acceso a los
endpoints REST de BORME API; le recomendamos el servidor alojado en
mcp.bormeapi.com. Ofrece las mismas herramientas que el servidor alojado, con
los mismos nombres, descripciones y parámetros, copiados en
[`tools.json`](tools.json). Cada llamada a una herramienta realiza una o varias
peticiones a `https://api.bormeapi.com/v1/...`. No contiene datos; los
directorios MCP crean una imagen a partir de su [Dockerfile](Dockerfile) para
listar las herramientas.

- Para listar las herramientas no necesita clave ni conexión a la red.
- Para llamar a una herramienta necesita una clave de API, salvo con
  `list_act_types` y `registry_stats`: a diferencia del servidor MCP alojado,
  la API REST no ofrece un plan gratuito sin clave. Su clave gratuita está en
  su [cuenta](https://bormeapi.com/es/account). Indíquela en
  `BORME_API_KEY`.
- `daily_digest` y `registry_stats` devuelven menos campos que en el servidor
  alojado, porque la API REST no tiene un único endpoint que
  los proporcione: `daily_digest` devuelve el número de eventos del día, el
  grado de estructuración de su texto y hasta 200 anuncios concursales, y
  `registry_stats` devuelve la fecha de la última publicación y, con clave,
  el grado de estructuración del texto en los últimos 30 días de
  publicación.
- No inicia sesión mediante OAuth.

Con Docker:

```bash
docker build -t borme-mcp .
docker run -i --rm -e BORME_API_KEY=SU_CLAVE borme-mcp
```

Con Python 3.12:

```bash
pip install -r requirements.txt
BORME_API_KEY=SU_CLAVE python server.py
```

Cuando el servidor alojado cambie sus herramientas, ejecute
`python scripts/update_tools.py` para regenerar `tools.json` y haga commit del
archivo actualizado. La CI falla mientras `tools.json` y el servidor alojado no
coincidan.

## Herramientas

- `search_companies`: busca sociedades por denominación actual o anterior y
  devuelve fichas ordenadas.
- `company_history`: la cronología registral de una sociedad: los actos
  publicados disponibles en su plan, del más reciente al más antiguo.
- `search_events`: busca anuncios del BORME por fecha, provincia, tipo de
  acto y denominación.
- `daily_digest`: un día de publicación en cifras, con sus anuncios
  concursales.
- `company_by_nif`: busca una sociedad por su NIF/CIF (plan Basic o
  superior).
- `brand_owner`: busca la sociedad a la que está vinculada una marca o un
  nombre comercial (plan Basic o superior).
- `company_brands`: marcas y nombres comerciales vinculados a una sociedad
  (plan Basic o superior).
- `recent_signals`: las señales de riesgo más recientes, como solicitudes de
  concurso o salidas masivas (plan Risk).
- `list_act_types`: los tipos de acto, con su etiqueta en inglés y el
  epígrafe original en español.
- `registry_stats`: tamaño y cobertura de los datos del registro.

La descripción y el esquema de parámetros de cada herramienta, tal como los
devuelve `tools/list`, explican sus parámetros. Están en inglés.

## Planes y límites

- **Sin clave o con clave gratuita:** 50 peticiones al día, eventos de los
  últimos 7 días, búsqueda de sociedades por nombre (primeros 5 resultados),
  historial de sociedades y resúmenes diarios dentro de esos 7 días, la lista
  de tipos de acto y las estadísticas del registro.
- **Basic:** 5.000 peticiones al día, 365 días de historial, búsqueda por
  NIF, el NIF en los resultados de la búsqueda de sociedades, y marcas y
  nombres comerciales.
- **Pro:** 50.000 peticiones al día y todo el historial desde 2009.
- **Risk:** 200.000 peticiones al día y la herramienta de señales de riesgo.

El servidor MCP utiliza la misma clave y la misma cuota diaria que la API
REST. Cada llamada a una herramienta cuenta como una petición en la cuota
diaria de su clave (o, sin clave, de su dirección IP). Los resultados tienen
un máximo por llamada (por ejemplo, 200 eventos); pagine con `offset` cuando
la herramienta lo ofrezca.

Planes y precios: [bormeapi.com/es#precios](https://bormeapi.com/es#precios).

## Datos

- Más de 9,6 millones de eventos desde 2009 del BORME-A (actos inscritos en
  el Registro Mercantil), actualizados cada día de publicación.
- Los resultados se basan en anuncios publicados en el BORME y otros datos
  públicos. Las asociaciones con marcas o NIF son coincidencias entre datos y
  no constituyen una confirmación jurídica.
- No se incluyen: cuentas anuales, anuncios del BORME-C (anuncios y avisos
  legales) ni anuncios publicados antes de 2009.

## En este repositorio

- [`skills/borme-registry-es`](skills/borme-registry-es/SKILL.md): una
  [Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
  que indica al agente qué herramienta usar, cómo encadenarlas y cómo
  presentar las respuestas. [`skills/borme-registry`](skills/borme-registry/SKILL.md)
  es la misma skill en inglés. Instale solo una de las dos. Para Claude Code:

  ```bash
  git clone https://github.com/bormeapi/borme-mcp.git
  mkdir -p ~/.claude/skills && cp -r borme-mcp/skills/borme-registry-es ~/.claude/skills/
  ```

  La skill necesita que el servidor MCP esté conectado.
- [`vocab/`](vocab/): el vocabulario de tipos de acto, cada valor con su
  epígrafe en español y su etiqueta en inglés.
- [`server.py`](server.py), [`tools.json`](tools.json) y el
  [`Dockerfile`](Dockerfile): el servidor stdio local descrito más arriba;
  [`scripts/update_tools.py`](scripts/update_tools.py) regenera `tools.json`
  a partir del servidor alojado.

## Enlaces relacionados

- Guía MCP: [bormeapi.com/es/mcp](https://bormeapi.com/es/mcp)
- Documentación de la API REST: [bormeapi.com/es/docs](https://bormeapi.com/es/docs)
- Actor de Apify: [Spain Company Registry - BORME Events](https://apify.com/zon4a/spain-company-registry-borme-events)
- Este repositorio: [github.com/bormeapi/borme-mcp](https://github.com/bormeapi/borme-mcp)

## Licencia

El contenido de este repositorio se distribuye bajo la [licencia MIT](LICENSE).

Los datos que sirve BORME API contienen información del sector público de la
Agencia Estatal Boletín Oficial del Estado (BORME), reutilizada conforme a la
Ley 18/2015 y el RD 1495/2011. No afiliado ni respaldado por el BOE.
