# Políticas de Detección de Fraude

## FP-01: Política de Montos Inusuales

**Descripción:**
Esta política detecta transacciones con montos significativamente superiores al comportamiento histórico del cliente. Los atacantes que comprometen cuentas suelen realizar transacciones de alto valor para maximizar el fraude antes de ser detectados.

**Criterios de Activación:**
- Monto de la transacción > 3x el promedio histórico del cliente
- Monto de la transacción > 2x el promedio Y fuera del horario habitual
- Incremento abrupto sin patrón de crecimiento gradual

**Umbrales Específicos:**
- Ratio crítico: > 3.0x promedio → acción inmediata
- Ratio elevado: > 2.0x promedio → verificación adicional
- Monto mínimo para evaluación: 100 PEN / 30 USD

**Acción Recomendada:**
CHALLENGE - Solicitar verificación adicional mediante OTP, pregunta de seguridad, o autenticación biométrica. Si el cliente no puede verificar su identidad, escalar a BLOCK.

**Contexto:**
Transacciones con montos inusuales son uno de los indicadores más confiables de fraude por cuenta comprometida o tarjeta clonada. El 78% de los fraudes confirmados involucran montos superiores a 2.5x el promedio del cliente.

---

## FP-02: Política de Transacciones Internacionales

**Descripción:**
Esta política evalúa transacciones originadas desde países diferentes al perfil geográfico habitual del cliente. Los fraudadores frecuentemente operan desde jurisdicciones extranjeras para dificultar la investigación y el rastreo.

**Criterios de Activación:**
- Transacción desde un país no registrado en el historial del cliente
- Transacción internacional dentro de 24 horas de una transacción doméstica (viaje imposible)
- Transacción desde país clasificado como alto riesgo según lista dinámica de FATF
- Primera transacción internacional para un cliente sin historial de viajes

**Umbrales Específicos:**
- Primera transacción en país nuevo: CHALLENGE
- Dos países diferentes en < 24 horas (imposibilidad geográfica): BLOCK
- País de alto riesgo + monto > 1000 USD: BLOCK
- País de riesgo medio + dispositivo desconocido: CHALLENGE

**Acción Recomendada:**
CHALLENGE para primer uso en país nuevo con monto moderado. BLOCK para escenarios de viaje imposible o combinación con otros factores de alto riesgo. Considerar whitelisting para clientes con historial de viajes frecuentes.

**Contexto:**
El fraude transfronterizo representa el 34% de las pérdidas totales por fraude. La verificación temprana en transacciones internacionales reduce pérdidas en un 67% según estudios de la industria. La coordinación legal entre países es compleja, haciendo crítica la prevención.

---

## FP-03: Política de Dispositivos No Reconocidos

**Descripción:**
Esta política detecta el uso de dispositivos (computadora, móvil, tablet) que nunca han sido asociados con la cuenta del cliente. La huella digital del dispositivo (device fingerprinting) es un control efectivo contra acceso no autorizado.

**Criterios de Activación:**
- Device ID no presente en el historial del cliente (primeros 90 días)
- Device ID nuevo + dirección IP de país extranjero
- Device ID nuevo + canal de alto riesgo (web browser desconocido, web_unknown)
- Device ID nuevo + cambio reciente de contraseña (< 48 horas)

**Umbrales Específicos:**
- Dispositivo nuevo solo (cliente con 1+ dispositivo previo): CHALLENGE
- Dispositivo nuevo + país extranjero: BLOCK
- Dispositivo nuevo + monto > 5x promedio: BLOCK
- Dispositivo nuevo + cambio de contraseña reciente: CHALLENGE con verificación reforzada

**Acción Recomendada:**
CHALLENGE para dispositivos nuevos con verificación mediante segundo factor. BLOCK automático si se combina con señales de alta sospecha (país extranjero, monto extremo). Permitir que el cliente registre el nuevo dispositivo tras verificación exitosa.

**Contexto:**
Los atacantes que comprometen credenciales operan desde dispositivos diferentes a los del cliente legítimo. El device fingerprinting detecta el 91% de intentos de acceso no autorizado. La tasa de falsos positivos es baja (< 5%) ya que los clientes legítimos rara vez cambian todos sus dispositivos simultáneamente.

---

## FP-04: Política de Horario de Operaciones

**Descripción:**
Esta política identifica transacciones realizadas fuera del horario habitual del cliente, basándose en el análisis de patrones temporales históricos. Muchos ataques ocurren de madrugada cuando el cliente está dormido y no puede responder a alertas.

**Criterios de Activación:**
- Transacción fuera del rango de usual_hours del cliente (ej: cliente opera 08:00-22:00, transacción a las 03:00)
- Transacción entre 00:00-06:00 para clientes sin historial nocturno documentado
- Transacción en horario inusual + monto elevado (> 2x promedio)
- Cambio abrupto de patrón temporal sin justificación (ej: cliente diurno hace transacción nocturna)

**Umbrales Específicos:**
- Fuera de horario solo (monto normal): señal informativa, no bloquear
- Fuera de horario + monto > 2x promedio: CHALLENGE
- Fuera de horario + monto > 3x promedio: BLOCK
- Madrugada (00:00-06:00) + dispositivo desconocido + monto elevado: BLOCK inmediato

**Acción Recomendada:**
APPROVE si es la única señal y el monto es habitual (cliente puede tener cambio legítimo de rutina). CHALLENGE si se combina con monto elevado. BLOCK si es madrugada con múltiples señales de riesgo. Enviar alerta al cliente independientemente de la decisión.

**Contexto:**
El 43% de los fraudes confirmados ocurren entre 00:00-06:00 hora local del cliente. Los atacantes explotan este período porque el cliente no puede responder a notificaciones push o SMS de verificación, permitiendo completar múltiples transacciones antes de ser detectados.

---

## FP-05: Política de Velocidad de Transacciones

**Descripción:**
Esta política detecta múltiples transacciones en un período corto de tiempo, un patrón característico de "card testing" (validación de tarjetas robadas) o ataques automatizados. Los fraudadores prueban listas de tarjetas robadas con transacciones pequeñas antes de realizar compras grandes.

**Criterios de Activación:**
- Más de 3 transacciones en 10 minutos desde el mismo cliente
- Más de 5 transacciones en 1 hora desde el mismo cliente
- Patrón de montos pequeños (< 50 USD) seguidos de un monto grande (> 500 USD)
- Múltiples transacciones fallidas por validación seguidas de una exitosa
- Velocidad inconsistente con comportamiento histórico (cliente promedio: 2 tx/día, súbito: 8 tx/hora)

**Umbrales Específicos:**
- 3-4 transacciones en 10 minutos: CHALLENGE con enfriamiento temporal (rate limiting)
- 5+ transacciones en 10 minutos: BLOCK temporal (30 minutos) + alerta
- Patrón de testing detectado (2+ tx pequeñas + 1 grande): BLOCK inmediato
- 10+ transacciones en 1 hora: BLOCK + escalamiento a revisión humana

**Acción Recomendada:**
BLOCK automático para velocidad extrema o patrón de card testing claro. CHALLENGE con rate limiting para velocidad moderada. Implementar captcha o verificación de segundo factor tras 3 transacciones en período corto. Considerar excepción para clientes con historial documentado de alta frecuencia (ej: comerciantes).

**Contexto:**
El card testing es la técnica #1 usada por atacantes para validar tarjetas robadas antes de venderlas en mercados clandestinos o usarlas para compras de alto valor. Un atacante puede probar 50-100 tarjetas en minutos usando scripts automatizados. La detección de velocidad bloquea el 89% de estos intentos.

---

## FP-06: Política de Combinación de Factores de Riesgo

**Descripción:**
Esta política evalúa la presencia simultánea de múltiples factores de riesgo que individualmente no son críticos pero en conjunto indican fraude con alta probabilidad. Es una meta-política que implementa análisis multifactorial para detectar fraude sofisticado que evade políticas individuales.

**Criterios de Activación:**
La política se activa cuando 2 o más de los siguientes factores están presentes simultáneamente:
- Monto elevado (> 2x promedio del cliente)
- País extranjero (no en usual_countries)
- Dispositivo no reconocido (no en usual_devices)
- Horario inusual (fuera de usual_hours)
- Canal de alto riesgo (web_unknown, mobile_unknown)
- Desviación comportamental alta (deviation_score > 0.7)
- Alerta de velocidad (velocity_alert = true)

**Umbrales Específicos:**
- 2 factores presentes: CHALLENGE con verificación estándar
- 3 factores presentes: BLOCK temporal + verificación reforzada (OTP + pregunta de seguridad)
- 4+ factores presentes: BLOCK + escalamiento automático a revisión humana (HITL queue)
- 5+ factores presentes: BLOCK + alerta de seguridad al cliente + congelamiento temporal de cuenta

**Acción Recomendada:**
CHALLENGE para 2 factores con verificación proporcional al riesgo. BLOCK para 3+ factores dado que la probabilidad de fraude supera el 85% según datos históricos. Escalar a revisión humana en casos de 4+ factores para investigación profunda. Notificar al cliente por múltiples canales (email, SMS, push notification) cuando se detecta combinación de 3+ factores.

**Contexto:**
El fraude sofisticado ha evolucionado para evitar disparar políticas individuales. Por ejemplo, un atacante puede usar un monto "solo" 2.1x el promedio (evitando umbral de 3x) pero combinado con país extranjero + dispositivo desconocido + horario nocturno. Esta política implementa scoring compuesto: cada factor suma puntos, y el total determina la acción. Detecta el 94% de fraudes que evaden políticas simples, reduciendo falsos negativos en un 73%.
