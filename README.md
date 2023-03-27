# Scora Scheduler

O Scora Scheduler é uma ferramenta para inicializar e desprovisionar recursos não utilizados ou fora de horario comercial.

## Aplicação
O código da aplicação roda em uma função Lambda, configurada através do Zappa. 

O trigger da função é feito através de Schedulers do AWS Event Bridge. Cada scheduler possui um horario, uma ActionType (representando start ou stop) e um TagValue (representando o horario no qual o scheduler é acionado).

A seleção de quais recursos devem ser alterados funciona a partir das tags:
```SCORA_SCHEDULER_AUTO_START```
```SCORA_SCHEDULER_AUTO_STOP```

Atualmente são suportadas as seguintes funcionalidades:
- ECS: Alterar a quantidade desejada e minima de tasks por serviço
- RDS: Pausar e startar DBs


Por padrão, inicializar um serviço no ECS atribui 1 task minima e 1 desejada, e parar 0 mínima e 0 desejada. Esse comportamento pode ser customizado através do parâmetro EcsServiceCountOverride, da seguinte forma:


```json
EcsServiceCountOverride = 
{
    "__service_name__": {
        "min_task_count": __min_task_count__, 
        "desired_task_count": __desired_task_count__
    }
}
```

O código para RDS foi retirado do [tutorial da AWS](https://aws.amazon.com/pt/blogs/database/schedule-amazon-rds-stop-and-start-using-aws-lambda/).

## Utilização

Caso o horário de agendamento desejado já exista, basta adicionar ao recurso a tag de start ou stop com o valor do horário.

Ex: 

SCORA_SCHEDULER_AUTO_START: 8h

SCORA_SCHEDULER_AUTO_STOP: 19h

Caso o horário não exista, basta criar um novo Scheduler no Event Bridge e passar a configuração desejada como parâmetro da função Lambda.

Caso deseje alterar apenas um recurso, pode passar o parâmetro ResourceArn ao invés de tagValue.


