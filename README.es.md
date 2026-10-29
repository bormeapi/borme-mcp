# Servidor MCP de BORME

*English: [README.md](README.md)*

Servidor MCP con los datos del **BORME** (Boletín Oficial del Registro
Mercantil), donde se publican los actos inscritos en el Registro Mercantil
español: más de 9,5 millones de eventos de sociedades desde 2009, actualizados
cada día hábil. Constituciones, nombramientos, concursos de acreedores,
ampliaciones y reducciones de capital: 52 tipos de acto, identificados con
enumerados en inglés.

## Endpoint alojado (sin instalación)

```json
{
  "mcpServers": {
    "borme": {
      "url": "https://mcp.bormeapi.com/mcp"
    }
  }
}
```

En Claude Code:

```bash
claude mcp add --transport http borme https://mcp.bormeapi.com/mcp
```

Solo lectura; `limit` es como máximo 200 por llamada. Sin clave funciona con el plan
gratuito: los últimos 7 días y 50 llamadas al día por dirección IP. Una clave
de API de [bormeapi.com/es/account](https://bormeapi.com/es/account), enviada
en la cabecera `X-API-Key`, activa su plan: `"headers": {"X-API-Key": "SU_CLAVE"}`
en los clientes que se configuran con JSON (el `mcp.json` de Cursor y similares) y `--header "X-API-Key: SU_CLAVE"` en `claude mcp add`.

- **free** (sin clave): los últimos 7 días
- **basic**: los últimos 365 días, más las consultas por NIF y por marca
- **pro**: todo lo de basic, con todo el histórico desde 2009
- **risk**: todo lo de pro, más la herramienta de señales de riesgo

Planes y precios: [bormeapi.com/es/precios](https://bormeapi.com/es/precios).

## Herramientas

| Herramienta | Qué hace | Desde el plan |
|---|---|---|
| `search_events` | Filtra eventos por rango de fechas, provincia, tipo de acto y nombre de la sociedad | free |
| `company_history` | La trayectoria de una sociedad (por slug o nombre), paginada, hasta donde alcance la ventana de su plan | free |
| `daily_digest` | La actividad registral de un día de publicación, agregada | free |
| `registry_stats` | Cobertura y grado de actualización del corpus | free |
| `list_act_types` | El vocabulario de tipos de acto: cada enumerado con su denominación original en español y su etiqueta en inglés | free |
| `company_by_nif` | Busca la sociedad que corresponde a un NIF o CIF (más de 520 000 correspondencias de fuentes públicas; si un NIF no aparece, significa «aún no vinculado») | basic |
| `brand_owner` | Qué sociedad es titular de una marca o un nombre comercial | basic |
| `company_brands` | Marcas y nombres comerciales de una sociedad | basic |
| `recent_signals` | Muestra de las últimas señales de riesgo derivadas, entre ellas declaraciones de concurso, sociedades fénix, ceses masivos de cargos y sociedades en el listado de deudores de la AEAT | risk |

## Skill para agentes

[`skills/borme-registry-es`](skills/borme-registry-es/SKILL.md) es una
[Agent Skill](https://platform.claude.com/docs/es/agents-and-tools/agent-skills/overview)
que indica al agente qué herramienta llamar, cómo encadenarlas (NIF → sociedad
→ historia, marca → sociedad → historia) y cómo presentar las respuestas: los
datos registrales tal como se publicaron, un NIF sin resultado como «aún no
vinculado» y las marcas separadas de las denominaciones sociales.
[`skills/borme-registry`](skills/borme-registry/SKILL.md) es la misma skill en
inglés. Instale solo una de las dos: cubren las mismas preguntas.

En Claude Code, copie la carpeta en su directorio de skills:

```bash
git clone https://github.com/bormeapi/borme-mcp.git
mkdir -p ~/.claude/skills && cp -r borme-mcp/skills/borme-registry-es ~/.claude/skills/
```

Otros agentes que leen carpetas con `SKILL.md` usan la misma carpeta en su
propio directorio de skills. La skill necesita que el servidor MCP de arriba
esté conectado.

## Ejemplos de preguntas

La primera funciona sin clave. Las otras dos necesitan una, porque el plan
gratuito solo ve los últimos 7 días; el histórico completo requiere pro.

- *«¿Qué sociedades de Valencia fueron declaradas en concurso de acreedores la semana pasada?»*
- *«Muéstrame la historia registral de Telefónica Audiovisual Digital»*
- *«¿Cuántas sociedades se constituyeron en Madrid en junio?»*

## Alojarlo usted mismo

`server.py` es un servidor de un solo archivo (FastMCP + psycopg) con un conjunto de
herramientas anterior al del endpoint alojado: no tiene planes ni claves, ni
herramientas de marcas (`brand_owner`, `company_brands`), ni paginación con
`offset` en `company_history`. La skill de arriba está escrita para el endpoint
alojado. El servidor lee una base de datos PostgreSQL con las tablas que
consulta, mediante un rol de solo lectura; ese esquema no forma parte de este
repositorio:

```bash
BORME_DSN=postgresql://user:pass@host/borme \
BORME_MCP_TRANSPORT=streamable-http \
python server.py
```

Qué supone construir el conjunto de datos por su cuenta:
[API de datos abiertos del BORME: XML público o inteligencia empresarial](https://bormeapi.com/es/blog/borme-open-data-api).

## Relacionado

- API REST con webhooks y listas de vigilancia: [bormeapi.com/es](https://bormeapi.com/es)
- Actor de Apify (feed de pago por evento): [Spain Company Registry - BORME Events](https://apify.com/zon4a/spain-company-registry-borme-events)

## Licencia

MIT (código del servidor). Actos registrales - fuente de los datos: Agencia
Estatal Boletín Oficial del Estado ([boe.es](https://www.boe.es)). Marcas y
nombres comerciales: Oficina Española de Patentes y Marcas (OEPM).
Correspondencias de NIF y parte de las señales de riesgo: otros datos abiertos
del sector público español. Información del sector público reutilizada
conforme a la Ley 37/2007.

Proyecto independiente: la Agencia Estatal Boletín Oficial del Estado y el
Registro Mercantil no participan en él, ni lo patrocinan ni lo respaldan.
