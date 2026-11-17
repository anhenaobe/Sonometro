# Oráculo de ruteo (Freerouting 2.1.0, solo para factibilidad)

No produce ruteo definitivo: sirve para saber si un conjunto de redes tiene solución en una capa y dónde tendría que
cruzar. Las pistas reales se dibujan a mano con `polilineas.py`.

## Etapa 1: redes críticas solas

```
python preparar.py <caso> <movs.json|-> 1
```

- Rutea solo las redes Analogica y Reloj, en F.Cu.
- Las salidas de los DAC pueden usar B.Cu.
- Todo lo demás queda como obstáculo, sin red.
- El ruteo de los bloques ya hechos queda fijo.

## Etapa 2: el resto de las redes

```
python etapa2.py <caso>
```

- Congela la etapa 1.
- Rutea la alimentación, I2C, DC_MON* y los straps con las dos capas.
- `cruces.py` lista cada tramo en B.Cu y qué pistas de F.Cu pasan por encima.

## Freerouting

```
java -jar freerouting-2.1.0.jar -de e.dsn -do e.ses --router.max_passes=100
```

- Agregar `--router.scoring.via_costs=5000` para minimizar vías.
- `sumar_ses.py` agrega el SES a la placa sin borrar el ruteo fijo. El importador de KiCad lo reemplaza.
