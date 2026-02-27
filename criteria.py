"""
Criterios de auditoría operativa Grido — Abril 2025
Cada ítem tiene: id, sección, nombre, tipo de check, y descripciones
de Conforme / Observación / No Conforme.
"""

LOCALES = ["Edén", "España"]

ROLES = ["operativo", "ejecutivo"]

TIPOS_AUDITORIA = ["completa", "parcial", "sorpresa_operativa"]

ROLES_RESPONSABLE = ["caja", "bodega", "limpieza", "encargada", "otro"]

ESTADOS_DESVIO = ["pendiente", "en_proceso", "cumplido", "incumplido"]

PRIORIDADES = ["alta", "media", "baja"]

TIPOS_DESVIO = ["operativo", "conductual", "estructural"]

SECTIONS = {
    "A": "Infraestructura — Estado de conservación y limpieza",
    "B": "Experiencia del cliente",
    "C": "Operatoria diaria",
    "D": "Imagen — Formato y Estética",
    "E": "Oferta y Stock",
}

CRITERIA: list[dict] = [
    # ── A. Infraestructura ──────────────────────────────────────────────
    {
        "id": "A.1",
        "section": "A",
        "name": "Exterior (pisos, zócalos, cordón cuneta, techos, muros, iluminación, pérgolas, toldos, bicicletero, dog parking y juegos infantiles): Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Pisos en perfecto estado; piezas sanas, homogéneas, zócalos completos, juntas bien tomadas. "
            "Rejillas sanas y bien instaladas. Deck pintado y fijado. Muros y cielorrasos sin humedad, "
            "rajaduras ni imperfecciones. Techos en buen estado. Pérgolas limpias. Bicicletero, dog parking "
            "y juegos infantiles en buen estado. Hasta 3 desvíos leves permitidos. Mínima falta de higiene "
            "(polvillo del momento, pequeñas manchas). Si se resuelve durante la auditoría → conforme."
        ),
        "observacion": (
            "Mínimo detalle de estructura. Zócalo un poco gastado o con mínima rotura sin riesgo. "
            "Deck con madera algo descolorida. Pequeños detalles de deterioro poco visibles (muro "
            "descascarado, agrietado, esquineros con roturas). Mínimos detalles de terminación."
        ),
        "no_conforme": (
            "Defectos evidentes de gran visibilidad que atentan contra la seguridad o la imagen de marca. "
            "Falta de tapa de desagüe, piezas rotas/faltantes muy visibles, piezas sueltas o con desniveles. "
            "Deck muy despintado, maderas levantadas/rotas/faltantes. Graffitis. Iluminación defectuosa. "
            "4 o más desvíos leves. Marcada falta de higiene: grasa acumulada, manchas de días anteriores, "
            "telas de araña, suciedad ajena al lugar."
        ),
    },
    {
        "id": "A.2",
        "section": "A",
        "name": "Marquesina: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Estructura en perfecto estado, toda la iluminación funcionando. Sin deterioro, rayadura, "
            "chapa abollada/rota, sin óxido. Chapa y corpóreo sanos. Cartel bandera y saliente en condiciones. "
            "Perfecto estado de limpieza."
        ),
        "observacion": (
            "Pequeños defectos de estructura que no afecten la imagen de marca. Rayaduras o roturas poco "
            "visibles. Mínima falta de higiene (polvillo, pequeñas manchas). Suciedad por lluvia del día anterior."
        ),
        "no_conforme": (
            "Defecto muy visible o grave. Lonas y chapas percudidas, rotas, oxidadas, despintadas. "
            "Logo corpóreo sin iluminación. Riesgo para la seguridad. Falta de marquesina. "
            "Reflectores apagados en horario nocturno. Marcada falta de higiene general."
        ),
    },
    {
        "id": "A.3",
        "section": "A",
        "name": "Mobiliario: Estado y limpieza (mesas, sillas, sombrillas, living)",
        "check": "OPERATIVO",
        "conforme": (
            "En excelente estado: sanos, pintados, ordenados, cantidad suficiente. Perfecto estado de limpieza."
        ),
        "observacion": (
            "Defectos poco significativos: rayaduras menores, presencia menor de óxido, caños apenas abollados. "
            "Sillas/mesas algo desordenadas. Detalles en tapizado. Falta de algunos regatones. "
            "Mínima falta de higiene."
        ),
        "no_conforme": (
            "Defecto visible que afecte la imagen o la seguridad. Superficies oxidadas, pintura muy desgastada, "
            "color no autorizado, caños desoldados. Tapas de mesas rotas, ploteos dañados. Living muy deteriorado. "
            "Sombrillas inestables. Marcada falta de higiene."
        ),
    },
    {
        "id": "A.4",
        "section": "A",
        "name": "Iluminación interior: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Artefactos sanos, sin defectos. Todas las luminarias funcionando y encendidas en horario nocturno. "
            "Perfecto estado de limpieza."
        ),
        "observacion": (
            "Leves defectos de estructura. Pocos plafones o lámparas quemadas. Pequeñas roturas. "
            "Mínima falta de higiene. Leve presencia de insectos."
        ),
        "no_conforme": (
            "Defectos visibles que afecten imagen o seguridad. Lámparas/LED/reflectores quemados. "
            "Plafones desprendidos. Luz insuficiente. Marcada falta de higiene. Marcada presencia de insectos."
        ),
    },
    {
        "id": "A.5",
        "section": "A",
        "name": "Pisos, aberturas, techo y zócalos en salón: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Pisos en perfecto estado, piezas sanas y homogéneas, zócalos completos, juntas bien tomadas. "
            "Sin humedad, rajaduras. Techos y cielorrasos en buen estado. Aberturas en perfecto estado, "
            "vidrios y herrajes sanos. Perfecto estado de limpieza."
        ),
        "observacion": (
            "Superficies con mínima rotura sin riesgo. Aberturas con pequeños detalles de estructura. "
            "Vinilo con pequeña rotura, vidrios con pequeñas rajaduras. Cortina metálica con graffitis "
            "visibles solo cuando está abierto. Mínima falta de higiene."
        ),
        "no_conforme": (
            "Defectos evidentes contra seguridad o higiene alimentaria. Falta de zócalos, tapa de desagüe, "
            "piezas rotas muy visibles. Obstrucciones en circulación. Alfombra deteriorada. Iluminación de "
            "garganta sin funcionar. Techos sin revocar. Puertas rotas o con mal funcionamiento. "
            "Marcada falta de higiene."
        ),
    },
    {
        "id": "A.6",
        "section": "A",
        "name": "Muros y revestimientos de muros en salón: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "En perfecto estado sin humedad, rajaduras. Superficies sanas y homogéneas. Revestimiento "
            "de madera nebraska en condiciones. Cuadros bien puestos. AMH con cerámicos bricks en excelente "
            "estado. Paredes interiores revocadas. Perfecto estado de limpieza."
        ),
        "observacion": (
            "Superficies con mínima rotura sin riesgo. Falta de zócalos o repisas. Módulos separados de "
            "la pared. Mínima falta de higiene."
        ),
        "no_conforme": (
            "Evidente falta de mantenimiento o deterioro: mucha humedad, pintura descascarada, "
            "cerámicos rotos/faltantes. Insumos ajenos a la marca visibles. Bricks deteriorados. "
            "Fallas que afecten seguridad alimentaria. Marcada falta de higiene."
        ),
    },
    {
        "id": "A.7",
        "section": "A",
        "name": "Cartelera: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Precios autorizados. Sabores faltantes marcados correctamente. Perfecto estado de limpieza."
        ),
        "observacion": (
            "Pequeños defectos de estructura que no afecten imagen. Falta de algún precio, cables visibles, "
            "marcos sueltos. Sabores faltantes no marcados. Mínima falta de higiene."
        ),
        "no_conforme": (
            "Defecto muy visible o grave. Pantallas azules o manchadas. Marcada falta de higiene. "
            "Imágenes desgastadas."
        ),
    },
    {
        "id": "A.8",
        "section": "A",
        "name": "Mostradores: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Estructura en perfecto estado. Vidrio templado en perfecto estado. Material de comunicación "
            "en formato autorizado, en buen estado y limpio."
        ),
        "observacion": (
            "Pequeños defectos de estructura. Iluminación parcial. Material de comunicación no autorizado. "
            "Mínima falta de higiene."
        ),
        "no_conforme": (
            "Defecto grave: piedra partida, luminaria sin funcionar, falta de acrílico protector, vidrios "
            "flojos/rajados/rotos, mostrador no fijado. Exhibición de productos vacíos. "
            "Marcada falta de higiene."
        ),
    },
    {
        "id": "A.9",
        "section": "A",
        "name": "Separación de áreas / Orden y estado del depósito",
        "check": "OPERATIVO",
        "conforme": (
            "Puerta de depósito señalizada. Correcta distribución y separación entre sectores. "
            "Instalaciones de material sanitario en buenas condiciones. Pisos sin roturas ni grietas. "
            "Iluminación adecuada. Estanterías/tarimas de material lavable. Recepción de pedidos sobre "
            "tarimas adecuadas."
        ),
        "observacion": (
            "Indicios de oxidación, pintura rayada. Puertas levemente descuadradas. Defectos de limpieza "
            "propios de la operatividad. Falta de señalización en puerta de depósito."
        ),
        "no_conforme": (
            "Sin división física entre sectores. Puertas rotas. Cortinas en lugar de puertas. "
            "Baños usados como depósitos. Instalaciones de madera sin tratar. Techos rotos. "
            "Elementos ajenos al sector. Estanterías de material no autorizado. Sin tarima de recepción. "
            "Marcada falta de higiene."
        ),
    },
    {
        "id": "A.10",
        "section": "A",
        "name": "¿El local permite descarga eficiente de productos congelados?",
        "check": "OPERATIVO",
        "conforme": (
            "El carrito/zorrita pasa por la puerta y se traslada sin inconvenientes. Rampas disponibles. "
            "Lugar para estacionar el camión. Nada atenta contra la calidad del producto ni la cadena de frío."
        ),
        "observacion": "No cumple con alguno de los requisitos.",
        "no_conforme": "",
    },
    {
        "id": "A.11",
        "section": "A",
        "name": "¿Hay espacio disponible para descansar?",
        "check": "OPERATIVO",
        "conforme": (
            "Se identifica un espacio limpio, de tamaño acorde a la cantidad de empleados, con espacio "
            "para sentarse y sin insumos ni mobiliario almacenado."
        ),
        "observacion": (
            "Existe espacio pero está sucio o se utiliza para almacenar insumos."
        ),
        "no_conforme": "No se identifica ningún espacio destinado a los colaboradores.",
    },
    # ── B. Experiencia del cliente ──────────────────────────────────────
    {
        "id": "B.1",
        "section": "B",
        "name": "Portal de Novedades, musicalización en exterior y en salón",
        "check": "OPERATIVO",
        "conforme": (
            "Música obligatoria en salón, agradable y variada, sonido adecuado. Equipo en buen estado. "
            "TV con portal de novedades en salón. LED o similar. Parlantes fuera de AMH y Caja."
        ),
        "observacion": (
            "TV de pulgadas inferiores al estándar. Equipo obstruyendo puesto operativo. Cables sueltos. "
            "Detalles de higiene. Imágenes desactualizadas. Leve desgaste."
        ),
        "no_conforme": (
            "Ausencia de música. TV transmitiendo telenovelas, partidos o noticias. TV ubicado en AMH. "
            "TV apagado. Falta de TV. Equipos no autorizados."
        ),
    },
    {
        "id": "B.2",
        "section": "B",
        "name": "Climatización y ventilación: Estado y limpieza",
        "check": "OPERATIVO",
        "conforme": (
            "Temperatura acorde. Equipo instalado, en excelente estado, con frigorías/calorías adecuadas. "
            "En funcionamiento si el clima lo requiere. Descarga de condensación prolija. Limpio."
        ),
        "observacion": (
            "Falla menor de estructura. Paleta/rejilla con roturas mínimas. Escaso polvillo."
        ),
        "no_conforme": (
            "Importante defecto o falla de seguridad. Falta de equipo, roto o apagado. Balde como recipiente "
            "de desagote. Filtros y rejillas sucios. Frigorías insuficientes. Carcasa con telas de araña. "
            "Mangueras con hongos. Estufas o ventiladores no autorizados."
        ),
    },
    {
        "id": "B.3",
        "section": "B",
        "name": "Dispenser de agua",
        "check": "OPERATIVO",
        "conforme": (
            "Equipo en perfecto estado y funcionamiento. Salida de agua adecuada. Refrigeración óptima. "
            "Agua caliente desactivada. Ubicado en salón (o AMH si el espacio no lo permite)."
        ),
        "observacion": (
            "Carcasa con pequeños defectos. Refrigeración deficiente. Roturas que permitan funcionamiento. "
            "Falta del receptáculo o rejilla. Falta de higiene del momento."
        ),
        "no_conforme": (
            "Ausencia de equipo o sin funcionamiento. Rotura grave o riesgo de seguridad. Agua caliente "
            "funcionando al alcance de clientes. Sin agua o vasos. Sin refrigeración. Ubicado fuera del salón/AMH. "
            "Falta de higiene evidente."
        ),
    },
    {
        "id": "B.4",
        "section": "B",
        "name": "Matafuegos, luces de emergencia, instalación eléctrica y señalética (Seguridad)",
        "check": "OPERATIVO",
        "conforme": (
            "Matafuegos: excelente estado, funcionando, bien instalado, accesible, limpio, carga habilitada, "
            "mínimo 5 kg, tipo ABC, colgado. Luz de emergencia: instalada y enchufada, una por sector. "
            "Desniveles señalizados en amarillo o rojo. Señalética de seguridad presente. "
            "Barandas bien instaladas. Instalación eléctrica sin cables a la vista."
        ),
        "observacion": (
            "Matafuegos/luz de emergencia con presencia de polvo. Deterioro poco visible en señalética. "
            "Barandas con leves detalles estéticos sin riesgo."
        ),
        "no_conforme": (
            "Ausencia de matafuegos o carga vencida. Sin luz de emergencia o desenchufadas. "
            "Desniveles sin señalización. Escaleras sin barandas. Cables a la vista, conexiones mal realizadas, "
            "enchufes sin tapas. Falta de disyuntor."
        ),
    },
    {
        "id": "B.5",
        "section": "B",
        "name": "Baño para clientes",
        "check": "OPERATIVO",
        "conforme": (
            "Puertas/aberturas en excelente estado. Extractores u ozonizadores funcionando. "
            "Sin pérdidas de agua. Inodoro con tapa y botón funcionando. Dispenser de jabón y papel "
            "con elementos. Espejos sanos con película antiestallido. Tela mosquitera sana. "
            "Señalizado. Limpio. Secamanos enchufado y funcionando."
        ),
        "observacion": (
            "Desgaste mínimo en elementos. Caños a la vista con conexiones en buen estado. "
            "Falta de higiene del momento. Falta de señalización. Secamanos desenchufado."
        ),
        "no_conforme": (
            "Puertas/divisorios defectuosos. Dispensers rotos, falta de jabón/toallas. Sin espejos o astillados. "
            "Sin extractor/ventiluz. Paredes con humedad. Iluminación deficiente. Paredes sucias, hongos. "
            "Baño inundado. Malos olores."
        ),
    },
    {
        "id": "B.6",
        "section": "B",
        "name": "Sector de juegos infantiles",
        "check": "OPERATIVO",
        "conforme": (
            "Juegos en perfecto estado con adecuado sistema de seguridad. Piso blando cubriendo toda la "
            "superficie. Perfecto estado de higiene."
        ),
        "observacion": (
            "Detalles mínimos de estructura. Juegos apenas despintados. Fallas apenas visibles. "
            "En exterior: falta de piso blando o césped. Detalles menores de higiene."
        ),
        "no_conforme": (
            "Defecto grave de seguridad o imagen de marca. Mal funcionamiento, partes mal fijadas, "
            "oxidadas, incompletas. Falta de piso de goma interior. Maquinitas en mal estado. "
            "Peloteros en salón. Importante falta de higiene."
        ),
    },
    {
        "id": "B.7",
        "section": "B",
        "name": "SmartFran - Club Grido Activo - Conexión y funcionamiento",
        "check": "OPERATIVO",
        "conforme": (
            "SmartFran instalado y funcionando. Club Grido activo, instalado, en funcionamiento (online). "
            "Lector de tarjetas funcionando. Tabla de canjes oficial impresa disponible."
        ),
        "observacion": (
            "No puede ingresar al sistema por problemas de conectividad. Tabla de canje no a la vista "
            "o material diferente al oficial. Colocadas en atriles."
        ),
        "no_conforme": (
            "No cuenta con sistema loyalty o sin funcionamiento. Falta de lector de tarjetas. "
            "No dispone de tabla de canjes oficial impresa."
        ),
    },
    {
        "id": "B.8",
        "section": "B",
        "name": "APP GRIDO: Gestión correcta del canal digital",
        "check": "OPERATIVO",
        "conforme": (
            "Local disponible en App Grido al menos en take away. Exhibe material de descarga de APP. "
            "Pedidos cancelados no superan los efectivos. Al menos un pedido efectivo en el último mes."
        ),
        "observacion": (
            "Local cerrado en App en take away. No exhibe material de descarga. "
            "Pedidos cancelados iguales a los efectivos."
        ),
        "no_conforme": (
            "No gestiona la APP Grido. Pedidos cancelados superan los efectivos. "
            "Sin pedidos efectivos en el último mes."
        ),
    },
    {
        "id": "B.9",
        "section": "B",
        "name": "Posnet y Grido Go (tótem autogestión)",
        "check": "OPERATIVO",
        "conforme": (
            "Posnet en correcto funcionamiento para tarjeta crédito/débito. Tótem de autogestión completo "
            "y funcionando."
        ),
        "observacion": (
            "Falta algún elemento del tótem. Deterioro o falta de higiene evidente."
        ),
        "no_conforme": (
            "No cuenta con posnet o no funciona. Pantalla del tótem apagada o fuera de funcionamiento."
        ),
    },
    {
        "id": "B.10",
        "section": "B",
        "name": "Disponibilidad de Wi-Fi para el cliente",
        "check": "OPERATIVO",
        "conforme": (
            "Wi-Fi disponible para clientes con señalética oficial indicando disponibilidad."
        ),
        "observacion": "Falta de señalética o leve deterioro.",
        "no_conforme": "No dispone de señal Wi-Fi para clientes.",
    },
    {
        "id": "B.11",
        "section": "B",
        "name": "¿Dispone de generador eléctrico?",
        "check": "OPERATIVO",
        "conforme": "Cuenta con generador eléctrico.",
        "observacion": "",
        "no_conforme": "No cuenta con generador eléctrico.",
    },
    # ── C. Operatoria diaria ────────────────────────────────────────────
    {
        "id": "C.1",
        "section": "C",
        "name": "Disponibilidad de productos a granel",
        "check": "OPERATIVO",
        "conforme": (
            "Disponibilidad total de productos a granel incluidos los de testeo."
        ),
        "observacion": (
            "Entre 1 y 4 faltantes de productos a granel (si los faltantes son por falta de disponibilidad "
            "de fábrica → conforme)."
        ),
        "no_conforme": (
            "5 o más faltantes de productos a granel."
        ),
    },
    {
        "id": "C.2",
        "section": "C",
        "name": "Disponibilidad y exhibición de productos secos e insumos generales",
        "check": "OPERATIVO",
        "conforme": (
            "Disponibilidad de toppings, crema, vasos, cucharitas, salsas, envases térmicos, servilleteros, "
            "servilletas. Grido Tops: mínimo 3 variedades. Exhibidora de tops sana y limpia. "
            "Grido Market y exhibidores en excelente estado, productos de frente, 3/4 completo."
        ),
        "observacion": (
            "Falta de hasta 2 insumos o variedades de salsa. Grido Tops: hasta 2 variedades. "
            "Detalles en vinilo o falta de higiene leve. Leve deterioro en Grido Market. "
            "Material de comunicación no autorizado o escrito a mano."
        ),
        "no_conforme": (
            "Faltan 3 o más insumos o variedades. No dispone de Grido Tops. Falta de exhibidora de tops "
            "o deterioro evidente. Falta de Grido Market. Productos no autorizados o cajas vacías."
        ),
    },
    {
        "id": "C.3",
        "section": "C",
        "name": "Condiciones de almacenamiento, fraccionamiento y rotulado",
        "check": "OPERATIVO",
        "conforme": (
            "Productos de distinta naturaleza no en misma estantería (o en orden correcto). "
            "Productos sobre tarimas a min 14 cm. Envases cerrados, sanos, protegidos. "
            "Etiquetas con datos reglamentarios. Productos fallados/vencidos separados e identificados. "
            "Fraccionados en recipientes plásticos aptos, herméticos. Registro de fraccionados completo (30 días)."
        ),
        "observacion": (
            "Falta de orden en rack o estantería. Leve manchas propios de la operatividad."
        ),
        "no_conforme": (
            "Cajas almacenadas sobre el piso. Envases abiertos/rotos. Sin diferencia entre circulación y estibación. "
            "Productos con etiqueta rota/borrosa. Productos vencidos sin identificación. "
            "Envases sucios o sin etiquetar. Registros incompletos o formato diferente."
        ),
    },
    {
        "id": "C.4",
        "section": "C",
        "name": "Equipos de frío (pozos, cámaras, freezer, exhibidora, toppinera, frigobar): Higiene y mantenimiento",
        "check": "OPERATIVO",
        "conforme": (
            "Materiales sanitarios, impermeables, resistentes. Freezer, exhibidoras, pozos y cámaras en buen "
            "estado y funcionamiento. Ploteo correcto. En buen estado de higiene sin acumulación de hielo. "
            "Toppinera y frigobar en buen estado. Cenefas y comunicación en correcto estado."
        ),
        "observacion": (
            "Detalles en el ploteo. Suciedad propia del momento. Leve acumulación de hielo. "
            "Rejilla de ventilación sucia. Precios escritos a mano."
        ),
        "no_conforme": (
            "Cámaras: falta de estantes, piso sanitario, mal cierre, burletes deteriorados. "
            "Freezer/exhibidoras: ploteo deteriorado, tapas rotas, burletes rotos, fallas eléctricas. "
            "Toppinera/frigobar: tapas rotas, temperatura fuera de rango. "
            "Suciedad adherida, hongos, hielo acumulado grueso."
        ),
    },
    {
        "id": "C.5",
        "section": "C",
        "name": "Temperatura de equipos de frío",
        "check": "OPERATIVO",
        "conforme": (
            "Granel: pozos/cámaras a -18°C. Granel mostrador: -13.5°C a -15°C. Impulsivos: -18°C. "
            "Sin cristalización ni signos de haber perdido consistencia."
        ),
        "observacion": "",
        "no_conforme": (
            "Variación de temperatura superior a 2°C de la ideal. Signos de haber perdido consistencia: "
            "cristalizados, arenosos, deformados. Granel en mostrador abiertos a mayor de -13.5°C."
        ),
    },
    {
        "id": "C.6",
        "section": "C",
        "name": "Capacidad de frío en la franquicia",
        "check": "OPERATIVO",
        "conforme": "Cantidad de bultos relevada adecuada.",
        "observacion": "",
        "no_conforme": "",
    },
    {
        "id": "C.7",
        "section": "C",
        "name": "Prevención de la contaminación cruzada",
        "check": "OPERATIVO",
        "conforme": (
            "Cuidado en manipulación de sabores. Respeto BPM. Cajas bien presentadas sin roturas. "
            "Helados bajados. Alisado solo al final de la jornada. Sin indicios de limpieza con esponjas. "
            "Colaboradores se lavan las manos con frecuencia. Cucuruchos con servilleta, térmicos por la base."
        ),
        "observacion": (
            "Fuera de hora pico: leve presencia de otros sabores o restos de cucuruchos. "
            "Un sabor sobrepasa el nivel. Cajas deterioradas o bajado desprolijo."
        ),
        "no_conforme": (
            "Presencia de hielo u otros sabores. Helados contaminados con material extraño. "
            "Interior de cajas completamente limpio (limpiado con esponja). No se respetan normas de "
            "manipulación. Uso de films para cierre. Mercadería al sol o más de 15 min fuera del freezer."
        ),
    },
    {
        "id": "C.8",
        "section": "C",
        "name": "Abastecimiento de agua",
        "check": "OPERATIVO",
        "conforme": (
            "Agua potable fría y caliente en AMH y depósito. Lavado de tanques 1 vez/año."
        ),
        "observacion": (
            "Sin agua caliente en depósito o no funciona. No se respeta frecuencia de lavado de tanques."
        ),
        "no_conforme": (
            "Sin agua caliente en AMH. Agua turbia. Larvas o gusanos en agua. Acumulación de tierra en tanque."
        ),
    },
    {
        "id": "C.9",
        "section": "C",
        "name": "AMH (Mesadas, bacha, lavabochero, grifo monocomando): Higiene y mantenimiento",
        "check": "OPERATIVO",
        "conforme": (
            "Bacha/lavabocheros/monocomando en perfecto funcionamiento. Buen suministro y desagüe. "
            "Mesadas y bajomesada autorizados, melamina sana, herrajes completos. Limpio."
        ),
        "observacion": (
            "Defectos visibles sin afectar seguridad alimentaria. Poca presión de agua. "
            "Suciedad propia de la operatividad. Falta de algún herraje. Restos de adhesivos."
        ),
        "no_conforme": (
            "Pérdidas de agua, falta de agua, desagüe defectuoso. Falta de monocomando. "
            "Grasa adherida, hongos. Muebles no autorizados, piedra agrietada, oxidados. "
            "Estantes forrados con bolsas/papel. Elementos ajenos al sector. Objetos personales visibles."
        ),
    },
    {
        "id": "C.10",
        "section": "C",
        "name": "Equipos de producción (licuadora, cremera, chocolatera, maq. café, bols, utensilios): Higiene y mantenimiento",
        "check": "OPERATIVO",
        "conforme": (
            "Materiales sanitarios. Licuadora, chocolatera, cremera completas, sanas, funcionando, a la vista. "
            "Cafetera, bols, dispenser completos con tapas. Utensilios de acero inoxidable en buen estado. "
            "6 paletas, 6 bocheros, 4 corvetes. Termómetro de punción funcionando. Todo limpio."
        ),
        "observacion": (
            "Ausencia de vaso medidor. Falta de perillas/manija. Derrames propios del momento. "
            "Bochero con medialuna trabada. Hasta 2 bocheros/paletas/corvetes menos."
        ),
        "no_conforme": (
            "Falta de equipos. Rosca de pico de cremera dañada. Cables dañados, vaso roto. "
            "Equipamiento no autorizado. Hongos en licuadora. Restos de crema en pico. "
            "Faltante de 3+ bocheros/paletas. Falta de termómetro. Mangos de madera. Paletas de aluminio."
        ),
    },
    {
        "id": "C.11",
        "section": "C",
        "name": "Equipos complementarios (balanza, microondas, caja, PC): Higiene y mantenimiento",
        "check": "OPERATIVO",
        "conforme": (
            "Equipos en buen estado. Balanza digital con visor a la vista del cliente. Microondas con display "
            "funcionando. Cables ordenados. Limpios."
        ),
        "observacion": (
            "Leve deterioro. Visor/botonera dañados. Microondas sin plato. Polvillo/manchas recientes. "
            "Papeles pegados con vista al colaborador."
        ),
        "no_conforme": (
            "Equipos fuera de funcionamiento. Paredes oxidadas, riesgo eléctrico. Ausencia de equipos. "
            "Vidrio/puerta/plato roto. Cables desordenados. Acumulación de residuos. Papeles pegados "
            "con vista al cliente."
        ),
    },
    {
        "id": "C.12",
        "section": "C",
        "name": "Elementos de higiene personal (dispenser jabón y toallas en depósito y AMH)",
        "check": "OPERATIVO",
        "conforme": (
            "Equipos sanos, con disponibilidad de jabón y papel, funcionando correctamente. Limpios."
        ),
        "observacion": (
            "Leve deterioro. Manchas recientes (helado, chocolate, almíbar)."
        ),
        "no_conforme": (
            "Dispensers rotos o ausentes. Falta de jabón/toallas. Despegados de la pared. "
            "Sostenidos con cintas. Suciedad adherida."
        ),
    },
    {
        "id": "C.13",
        "section": "C",
        "name": "Elementos de limpieza y desinfección. Ausencia de sustancias peligrosas",
        "check": "OPERATIVO",
        "conforme": (
            "Productos en sector definido e identificado, separados de materia prima. Productos autorizados. "
            "Rejillas/esponjas enteras y sanas, colores diferenciados (AMH: blanco, salón/exterior: amarillo, "
            "baño: otro color). Escobillón/escoba/pala con cabos de plástico o metal forrado. "
            "Productos químicos en envases sanos, cerrados, identificados. Sin sustancias peligrosas."
        ),
        "observacion": (
            "Hasta 2 rejillas menos de lo exigido. Jabón en pan y esponja sobre mesada. "
            "Mangos de madera sin forrar."
        ),
        "no_conforme": (
            "Productos no autorizados. Rejillas con roturas, mezcladas, rejilla no autorizada. "
            "Menos de la mitad de rejillas exigidas. Esponjas metálicas en AMH. Elementos deteriorados/sucios. "
            "Productos químicos abiertos, rotos, sin identificación. Presencia de plaguicidas, venenos, "
            "nafta, solventes, insecticidas."
        ),
    },
    {
        "id": "C.14",
        "section": "C",
        "name": "¿El baño de los colaboradores está en condiciones?",
        "check": "OPERATIVO",
        "conforme": (
            "Limpio, incluido paredes, techos, pisos, extractores. Ventiluz con tela mosquitera limpia. "
            "Con papel higiénico, toalla de mano y jabón."
        ),
        "observacion": "Falta de higiene del momento no corregida.",
        "no_conforme": (
            "Paredes sucias, hongos, pérdida de agua, extractores sucios, baño inundado, malos olores, "
            "telas de araña, mosquiteras con tierra."
        ),
    },
    {
        "id": "C.15",
        "section": "C",
        "name": "Higiene y Salud del Colaborador",
        "check": "OPERATIVO",
        "conforme": (
            "Correcto aseo personal. Pelo limpio, uñas cortas y limpias. Lavado de manos con frecuencia. "
            "Sin maquillaje, esmalte de uñas ni objetos de adorno. Pelo recogido con cofia. Sin barba. "
            "Correctos hábitos de higiene. Sin heridas cortantes en AMH."
        ),
        "observacion": "",
        "no_conforme": (
            "Falta de higiene percibida, uñas largas/sucias. No respeta lavado de manos. "
            "Maquillaje, uñas pintadas, adornos (cadenas, anillos, pulseras, aros). Cabello suelto. Barba. "
            "No respetar normas de manipulación. Manipular celular y luego helado. "
            "Heridas cortantes expuestas en AMH."
        ),
    },
    {
        "id": "C.16",
        "section": "C",
        "name": "Uniforme del Colaborador",
        "check": "OPERATIVO",
        "conforme": (
            "Uniformes en excelente estado, sin roturas ni remiendos, sin desteñir. Acorde al sector. "
            "Calzado cerrado. Uniforme actualizado (cofia, delantal jean, remera, pantalón jean)."
        ),
        "observacion": "",
        "no_conforme": (
            "Colaboradores ingresando con ropa de trabajo. Uniformes rotos/deshilachados, desteñidos, "
            "sucios, arrugados. Falta de elementos. Calzado abierto (crocs, alpargatas). Logo desactualizado."
        ),
    },
    {
        "id": "C.17",
        "section": "C",
        "name": "Conocimiento del colaborador",
        "check": "OPERATIVO",
        "conforme": "Responde correctamente pregunta aleatoria de productos o procedimientos.",
        "observacion": "",
        "no_conforme": "Desconoce el producto/procedimiento y no puede acceder a la información.",
    },
    {
        "id": "C.18",
        "section": "C",
        "name": "Constancia AFIP, Inscripción Provincial, Habilitación Municipal, Carnet Sanitario y Control de plagas",
        "check": "OPERATIVO",
        "conforme": (
            "Toda la documentación requerida disponible. Todo el personal con carnet de manipulador. "
            "Certificado de desinfección exhibido a 30 días y formulario MIP."
        ),
        "observacion": (
            "Falta un documento. Al menos un colaborador sin carnet vigente en el local. "
            "Certificado vencido. MIP incompleto."
        ),
        "no_conforme": "",
    },
    # ── D. Imagen – Formato y Estética ──────────────────────────────────
    {
        "id": "D.1",
        "section": "D",
        "name": "Exterior (pisos, zócalos, muros, iluminación, pérgolas y toldos): Formato",
        "check": "COMERCIAL",
        "conforme": (
            "Formato según planilla técnica. Techos/cielorrasos del mismo color que muros exterior. "
            "Pérgolas según ficha técnica. Cajón de cortina metálica del color de muros. "
            "Correcta colocación de motores de aire."
        ),
        "observacion": "",
        "no_conforme": (
            "Paredes de color no autorizado. Toldos de colores no autorizados, logo desactualizado. "
            "Iluminación fuera de formato. Pérgolas fuera de ficha técnica."
        ),
    },
    {
        "id": "D.2",
        "section": "D",
        "name": "Marquesina: formato",
        "check": "COMERCIAL",
        "conforme": (
            "Marquesina con logo nuevo. Saliente con imagen nueva. Cartel bandera actualizado. Brazos reflectores LED."
        ),
        "observacion": "",
        "no_conforme": "Marquesina con logo viejo. Cartel bandera desactualizado. Falta de marquesina.",
    },
    {
        "id": "D.3",
        "section": "D",
        "name": "Comunicación en vidriera",
        "check": "COMERCIAL",
        "conforme": (
            "Faja esmerilada con diseño correcto a 90 cm del piso. Al menos un soporte de comunicación "
            "autorizado bien colocado y actualizado. Microperforados y vinilos en condiciones. "
            "Puerta: carteles de servicio autorizados (abierto-cerrado/horarios, Club Grido, WiFi). "
            "Precios autorizados."
        ),
        "observacion": (
            "No cumple con uno de los requisitos. Franja gris lisa. Microperforados con mínimos detalles. "
            "Falta un cartel obligatorio o desactualizado."
        ),
        "no_conforme": (
            "No cumple con 2+ requisitos. Precios no autorizados. Vidriera cargada con más de 2 soportes. "
            "Soportes mal colocados o vacíos. Cartelería hecha a mano o ajena. Material Covid. "
            "Formatos no autorizados."
        ),
    },
    {
        "id": "D.4",
        "section": "D",
        "name": "Mobiliario exterior: formato (mesas, sillas, sombrillas, cerco)",
        "check": "COMERCIAL",
        "conforme": (
            "Mesas blancas lisas, sillas ONE (blanco, azul, rojo o naranja) o Río. No convivencia de "
            "ONE naranjas y rojas, ni ONE y Río en mismo sector. Sombrillas blancas o azules según ficha. "
            "Bancos metálicos azules o de madera según ficha (no pueden convivir)."
        ),
        "observacion": "",
        "no_conforme": (
            "Sillas que no son ONE o Río. Sillas ONE amarillas. Convivencia naranja y rojo. "
            "Convivencia ONE y Río en mismo sector. Sombrillas fuera de formato. "
            "Comunicación no autorizada en mesas/servilleteros."
        ),
    },
    {
        "id": "D.5",
        "section": "D",
        "name": "Mobiliario interior: formato (mesas, sillas, living)",
        "check": "COMERCIAL",
        "conforme": (
            "Mesas blancas lisas, sillas ONE o Río (mismas reglas de no convivencia). "
            "Barras blancas con banquetas MILO. Living: butacón BARI con mesa ratona de madera "
            "o sillón PAMPA con mesa ratona blanca."
        ),
        "observacion": "",
        "no_conforme": (
            "Sillas fuera de formato. Convivencias no autorizadas. Bancos metálicos en salón. "
            "Comunicación no autorizada en mesas/servilleteros."
        ),
    },
    {
        "id": "D.6",
        "section": "D",
        "name": "Iluminación interior: formato",
        "check": "COMERCIAL",
        "conforme": (
            "Artefactos autorizados según planilla técnica (plafones LED compactos, riel blanco, galponeras, "
            "bandejas). Luz fría o neutra en AMH, cálida o neutra en sitting."
        ),
        "observacion": "",
        "no_conforme": (
            "Lámparas colgantes no autorizadas o deterioradas. Iluminación fuera de formato."
        ),
    },
    {
        "id": "D.7",
        "section": "D",
        "name": "Pisos, aberturas, techo y zócalos en salón: Formato",
        "check": "COMERCIAL",
        "conforme": (
            "Formato según planilla técnica. Techos/cielorrasos del mismo color que muros. "
            "Iluminación de garganta AMH con luces blancas, cálidas o neutras. Color autorizado. "
            "Cortinas blackout solo en sitting como protección solar."
        ),
        "observacion": "",
        "no_conforme": (
            "Alfombra deteriorada o desactualizada. Cortinas de material/color no autorizado. "
            "Iluminación de color no autorizada. Material promocional colgado del techo no autorizado."
        ),
    },
    {
        "id": "D.8",
        "section": "D",
        "name": "Muros y revestimientos en salón: formato",
        "check": "COMERCIAL",
        "conforme": (
            "Ploteos actualizados. Paredes de color autorizado. Revestimiento de madera en condiciones. "
            "Cuadros con imágenes autorizadas. AMH con cerámicos bricks. Zócalos y repisas corian. "
            "Rollos de cortina cubiertos con caja de durlock."
        ),
        "observacion": "",
        "no_conforme": (
            "Ploteos no autorizados o desactualizados. Paredes de color no autorizado. "
            "Sin cerámicos bricks. Estantes no autorizados. Falta de zócalos/repisas. "
            "Empapelado con logo viejo. Material de comunicación no autorizado en paredes."
        ),
    },
    {
        "id": "D.9",
        "section": "D",
        "name": "Cartelera: formato",
        "check": "COMERCIAL",
        "conforme": (
            "Cartelera digital vigente. TVs de 43 pulgadas, alineados. Legible desde caja. "
            "Carta de productos para Take Away exterior. Precios autorizados. "
            "Sabores faltantes marcados correctamente."
        ),
        "observacion": (
            "TVs con soporte nuevo pero desalineados o con diferencia de tamaño mínimo."
        ),
        "no_conforme": (
            "Cartelera desactualizada o tradicional no autorizada. Pantallas menores a 43 pulgadas. "
            "Sabores faltantes no marcados."
        ),
    },
    {
        "id": "D.10",
        "section": "D",
        "name": "Mostradores: formato",
        "check": "COMERCIAL",
        "conforme": "Modelo nebraska/báltico. Material de comunicación autorizado.",
        "observacion": (
            "Formato Nebraska con logo desactualizado. Iluminación parcial. "
            "Material de comunicación no autorizado/desactualizado."
        ),
        "no_conforme": (
            "Modelo distinto al nebraska/báltico. Falta parcial de vidrios. Productos vacíos en mostrador."
        ),
    },
    {
        "id": "D.11",
        "section": "D",
        "name": "Decoración, plantas, jardines y cestos",
        "check": "COMERCIAL",
        "conforme": (
            "Plantas y decoraciones en excelente estado. Decoraciones de fechas especiales completas. "
            "Cestos plásticos tapa vaivén y de chapa autorizados. Baños con modelo a pedal."
        ),
        "observacion": "No cumple con uno de los requisitos.",
        "no_conforme": (
            "No cumple con 2+ requisitos. Soporte de vereda escrito a mano o con afiches no autorizados."
        ),
    },
    {
        "id": "D.12",
        "section": "D",
        "name": "Sector de juegos infantiles (formato)",
        "check": "COMERCIAL",
        "conforme": (
            "Juegos en perfecto estado con seguridad adecuada. Piso blando cubriendo toda la superficie. "
            "Máximo una máquina por franquicia, en sector infantil definido."
        ),
        "observacion": (
            "Detalles mínimos de estructura. Fallas apenas visibles. "
            "En exterior: falta de piso blando/césped."
        ),
        "no_conforme": (
            "Defecto grave de seguridad. Falta de piso de goma interior. 2+ maquinitas. "
            "Maquinitas en mal estado. Peloteros en salón. Falta de juegos en sector definido."
        ),
    },
    {
        "id": "D.13",
        "section": "D",
        "name": "Circuito ingreso-compra-consumo-salida: ¿es claro y cómodo?",
        "check": "COMERCIAL",
        "conforme": (
            "AMH enfrentado a la puerta. Autoservicio antes/junto a caja. Cliente visualiza productos "
            "antes de llegar a caja. Sector infantil fuera de zona de riesgo. Recorrido claro sin obstáculos."
        ),
        "observacion": "",
        "no_conforme": "",
    },
    {
        "id": "D.14",
        "section": "D",
        "name": "¿La cantidad de puestos de trabajo y cajas es coherente con las ventas?",
        "check": "COMERCIAL",
        "conforme": (
            "Puestos coherentes: ≥30 mil kg = 1 puesto, 30-45 mil kg = 1.5 puestos, ≥45 mil kg = 2 puestos. "
            "≥45 mil kg = 2 cajas."
        ),
        "observacion": "",
        "no_conforme": "",
    },
    {
        "id": "D.15",
        "section": "D",
        "name": "¿La franquicia se encuentra ordenada?",
        "check": "COMERCIAL",
        "conforme": (
            "Mesas con distanciamiento mínimo. Sectores diferenciados e identificables. "
            "Servicios complementarios correctamente implementados."
        ),
        "observacion": "",
        "no_conforme": "",
    },
    {
        "id": "D.16",
        "section": "D",
        "name": "En términos generales, ¿el local cumple con los requisitos de la marca?",
        "check": "COMERCIAL",
        "conforme": "100% vinculado a la infraestructura del local (no distribución, formato o limpieza).",
        "observacion": "",
        "no_conforme": "",
    },
    # ── E. Oferta y Stock ───────────────────────────────────────────────
    {
        "id": "E.1",
        "section": "E",
        "name": "Disponibilidad y exhibición de impulsivos",
        "check": "COMERCIAL",
        "conforme": (
            "Disponibilidad total de productos envasados incluidos testeo. Exhibidoras con vinilo simil "
            "acero inoxidable autorizado. Productos exhibidos verticalmente (vertical) u horizontalmente "
            "(horizontal) y de cara al cliente. Exhibidoras al menos 3/4 completas. "
            "Vinilos de promociones autorizados y en buen estado."
        ),
        "observacion": (
            "Hasta 2 productos envasados faltantes. Espacios vacíos en exhibidora. Cenefa desactualizada. "
            "Desorden no resuelto. 2 productos no de frente. Vinilos no autorizados/deteriorados."
        ),
        "no_conforme": (
            "3+ productos no disponibles. No cumple con 2+ requisitos. Pozos/freezers operativos en salón. "
            "Falta de ploteo o deterioro evidente. Vidrios rajados. Exhibidoras no autorizadas. "
            "Ocupación inferior a 3/4. Precios en papel o fibrón."
        ),
    },
    {
        "id": "E.2",
        "section": "E",
        "name": "Disponibilidad y exhibición de congelados (Frizzio)",
        "check": "COMERCIAL",
        "conforme": (
            "Exhibidora exclusiva de alimentos congelados con al menos un producto de cada familia. "
            "Cenefa Frizzio actualizada. Al menos una pieza de comunicación en vidriera o sector de caja. "
            "Vinilo simil acero inoxidable. Exhibidoras al menos 3/4 completas."
        ),
        "observacion": (
            "Falta hasta 2 líneas de productos. Falta de cenefa o desactualizada. "
            "Falta de comunicación Frizzio. Falta de precios en vinilo."
        ),
        "no_conforme": (
            "No tiene exhibidora exclusiva. No tiene toda la familia de productos. "
            "Productos desordenados. Exhibidora con ocupación inferior a 3/4. Precios en papel o a mano."
        ),
    },
    {
        "id": "E.3",
        "section": "E",
        "name": "¿Posee cámara de frío?",
        "check": "COMERCIAL",
        "conforme": "Sí. Puede estar en la franquicia o por fuera.",
        "observacion": "",
        "no_conforme": "No.",
    },
    {
        "id": "E.4",
        "section": "E",
        "name": "¿La cámara de frío tiene estantes?",
        "check": "COMERCIAL",
        "conforme": "Sí (estantes y palets, piso sanitario).",
        "observacion": "Combina ambos recursos.",
        "no_conforme": "No. Solo tiene pallet o piso sanitario.",
    },
    {
        "id": "E.5",
        "section": "E",
        "name": "¿Cumple con capacidad de frío ideal?",
        "check": "COMERCIAL",
        "conforme": (
            "La capacidad real coincide con el 90% de lo comprado en diciembre 2022."
        ),
        "observacion": (
            "La capacidad real coincide con el 80% de lo comprado en diciembre 2022."
        ),
        "no_conforme": (
            "La capacidad real no llega al 80% de lo comprado en diciembre 2022."
        ),
    },
]


def get_criteria_by_section(section: str) -> list[dict]:
    return [c for c in CRITERIA if c["section"] == section]


def get_criterion_by_id(criterion_id: str) -> dict | None:
    for c in CRITERIA:
        if c["id"] == criterion_id:
            return c
    return None


def get_section_name(section: str) -> str:
    return SECTIONS.get(section, section)
