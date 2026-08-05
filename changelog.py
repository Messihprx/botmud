VERSION = "2.7.1"

CHANGELOGS = [
    {
        "version": "v2.7.1",
        "emoji": "✨",
        "changes": [
            "**Melhoria na criação de parcerias:** Agora a tag pode ter até 6 caracteres, e o que você digitar nela é mantido do jeito que foi escrito, sem alterar para maiúsculo. O limite do nome do clã também foi ajustado."
        ]
    },
    {
        "version": "v2.7",
        "emoji": "📅",
        "changes": [
            "**Atualização no filtro de pesquisa:** Agora o comando /tab possui filtro pra puxar somente quem recrutou de uma certa pessoa.",
            "**Filtro de mês no /tab:** Agora o /tab possui um novo filtro pra filtrar por mês, quantos recrutados foram daquele mês, e também é possível ver o ranking por mês."
        ]
    },
    {
        "version": "v2.6.1",
        "emoji": "📅",
        "changes": [
            "**Correção no comando ficha:** Agora o comando ficha também funciona com o nick do Roblox."
        ]
    },
    {
        "version": "v2.6",
        "emoji": "📅",
        "changes": [
            "**NOVA ADIÇÃO PRO BOT COM PARCERIAS**",
            "**Comando /addparceria**: Adicionado um comando de barra para criar parcerias com cargos e tags automáticas. Agora é possível criar convites personalizados que, ao serem usados, atribuem um cargo específico e adicionam uma tag ao nome do usuário, facilitando a gestão de parcerias e promoções dentro do servidor."
            "**Comando /listarparcerias**: Adicionado um comando de barra para listar todas as parcerias registradas e suas estatísticas."
            "**Comando /removerparceria**: Adicionado um comando de barra para remover parcerias registradas, permitindo uma gestão mais eficiente das parcerias ativas no servidor."
        ]
    },
    {
        "version": "v2.5.1",
        "emoji": "📅",
        "changes": [
            "**Funcionalidades aprimoradas**",
            "**Comando =niver**: Ajeitado a hora global para dar parabens no momento certo."
            "**Comando hora**: Adicionado uma função para ver a hora atual usando `=botinfo`."
            "**Implementação IA:** Uma IA gera o texto de parabéns para o membro." 
            "**Melhorias e correções:** Correção de bugs do comando =niver e do horário global." 
        ]
    },
    {
        "version": "v2.5",
        "emoji": "📅",
        "changes": [
            "**Novas Funções para o clã**",
            "**Adicionada função de gerenciamento de gema do clã**: Foram criados comandos novos de gerenciamento de banco do clã, agora pode gerenciar as gemas do clã, adicionar, remover, ver extrato e saldo com /banco, /adicionar, /retirar e /extrato." 
            "**Aniversário**: Agora o bot tem uma função de aniversário, onde os usuários podem cadastrar suas datas de nascimento e o bot irá anunciar no canal um dia antes do aniversário do usuário, para que todos possam parabenizar e comemorar juntos! Para cadastrar sua data de nascimento, basta usar o comando `=niver DD/MM ou <dia> <mês>` (exemplo: `=niver 25/12 ou 25 12`)." 
            "**Atualizações futuras:** Ajeitar o comando =niver pra fazer ele dar aniversário pra pessoa no canal específico."     
        ]
    },
    {
        "version": "v2.4.3",
        "emoji": "📅",
        "changes": [
            "**Pequenos ajustes.**",
            "**Correção na marcação de membros na tradução:** Agora, ao traduzir uma mensagem que menciona um usuário, o bot não marca mais o usuário nem nenhuma menção."       
        ]
    },
    {
        "version": "v2.4.2",
        "emoji": "📅",
        "changes": [
            "**Pequenos ajustes.**",
            "**Criação do =langs:** Mostra todos os idiomas disponíveis para tradução.(CUIDADO POIS ENVIA MUITAS EMBEDS POIS HÁ MUITOS IDIOMAS).",
            "**Adicionado bandeiras novas pra ser reagida com a bandeira. (filipinas)"          
        ]
    },
    {
        "version": "v2.4.1",
        "emoji": "📅",
        "changes": [
            "**Pequenas alterações.**",
            "**Alteração no /ficha:** Agora a ficha apaga depois de 60 segundos para evitar poluição de mensagens no canal de recrutamento.",
            "**Alteração no /edit e /delete:** Para monitoramento de ações no servidor, foi adicionado logs para todas as ações de edição e exclusão de fichas."          
        ]
    },
    {
        "version": "v2.4",
        "emoji": "📅",
        "changes": [
            "**Pequenas correções de bugs e funções nos comandos.**",
            "**Correção no /edit:** Os Recrutadores não conseguiam editar a ficha, mesmo sendo deles, bug resolvido",
            "**Limite nos caracteres do recrutamento:** Agora no comando `/rec` o nome do recrutado tem um limite de caracteres para impedir bug de não conseguir trocar o nome."          
        ]
    },
    {
        "version": "v2.3",
        "emoji": "📅",
        "changes": [
            "**Melhoria na tradução:** Agora o bot traduz uma mensagem ao reagir com uma bandeira, e a mensagem de tradução é enviada como resposta à mensagem original, proporcionando uma experiência mais fluida e organizada.",
            "**Correção do setlang:** Agora o setlang após 1 minuto apaga automaticamente a mensagem traduzida.",    
            "**Atualização do Bot com IA:** Agora o bot tem IA imbutido abrindo espaço para novas funcionalidades futuras.",
            "**Criação do comando insulto e resumo:** Comando `=insulto @alguém` para gerar um insulto criativo e engraçado sobre a pessoa marcada, usando a IA. O comando `=resumo` para gerar um resumo engraçado das últimas mensagens do canal, também usando a IA."
            "**Comando gay para zoeiras:** Comando `=gay` para gerar uma mensagem aleatória de um usuário marcado como gay."          
        ]
    },
    {
        "version": "v2.2",
        "emoji": "📅",
        "changes": [
            "**Melhoria no edit:** Ao editar um recrutamento, o bot agora baixa a imagem enviada pelo usuário, faz o upload para o banco de dados. Isso garante que as imagens sejam armazenadas de forma segura e acessível, além de permitir a remoção de imagens antigas para economizar espaço.",
            "**Correção de bugs:** bugs na tradução foram corrigidos.",
            "**Ajuste no changelog:** Atualização do changelog para mudar entre as páginas"         
        ]
    },
    {
        "version": "v2.1",
        "emoji": "📅",
        "changes": [
            "**Criação do comando /excel:** Comando `/excel` para gerar uma planilha Excel com todos os recrutamentos.",
            "**Edição do comando recentes pra tab:** O comando `/recentes` foi renomeado para `/tab` para melhor refletir sua funcionalidade de mostrar os recrutamentos mais recentes em formato de tabela.",
            "**Melhoria ao terminar registro:** Ao finalizar um registro, o bot agora envia o ID de recrutamento criado para o canal de recrutamento, facilitando a referência e acompanhamento dos recrutamentos.",
            "**Criação do delete:** Comando `/delete` para excluir fichas dee recrutamento.",
            "**Criação do ranking de recrutadores:** Implementação de um sistema de ranking para os recrutadores, baseado no número de recrutamentos realizados, incentivando a participação e engajamento da comunidade.",
            "**Correção de bugs e melhorias técnicas:** Pequenas correções e melhorias de desempenho para garantir uma experiência mais fluida e estável."
        ]
    },
    {
        "version": "v2.0",
        "emoji": "📅",
        "changes": [
            "**Criação do comando /rec:** Comando `/rec` para automatizar recrutamento de novos membros.",
            "**Criação do comando /ficha:** Comando `/ficha` para mostrar detalhes do recrutamento.",
            "**Criação do comando /edit:** Comando `/edit` para editar informações do recrutamento.",
            "**Criação dos recentes:** Comando `/recentes` para mostrar os recrutamentos mais recentes.",
            "**Atualização do funcionamento do bot:** O bot foi ajustado para suportar mais comandos e funcionalidades, além de melhorias de desempenho e estabilidade.",
            "**Correção de bugs:** Pequenas correções e melhorias de desempenho."
            "**Melhoria no banco de dados:** Adição de novas tabelas e campos para suportar as novas funcionalidades de recrutamento."
            
        ]
    },
    {
        "version": "v1.5.1",
        "emoji": "📅",
        "changes": [
            "**Criação do perfil:** Comando `=profile` para mostrar informações do usuário.",
            "**Melhoria no Top:** Agora o comando `=top` mostra o XP (número de traduções) de cada usuário e marcando o usuário com mais XP.",
            "**Retirada do Original no translate:** Removido o texto original da mensagem traduzida do comando `=translate` para uma experiência mais limpa.",
            "**Criação do =addlang:** Comando `=addlang` para adicionar UM novo idioma para traduzir.",
            "**Criação do =removelang:** Comando `=removelang` para remover UM idioma da lista de idiomas para traduzir.",
            "**Correção de bugs:** correção do setlang para adms."
        ]
    },
    {
        "version": "v1.5.0",
        "emoji": "📅",
        "changes": [
            "**Criação do top:** Comando `=top` para mostrar os usuários com mais traduções.",
            "**Futuramente:** Planejamento de novas funcionalidades e melhorias contínuas relacionadas a perfil.",
        ]
    },
    {
        "version": "v1.4",
        "emoji": "📅",
        "changes": [
            "**Retirada do Original:** Removido o texto original da mensagem traduzida para uma experiência mais limpa.",
            "**Implementação do /translate:** Comando slash `/translate` para traduzir textos de forma privada.",
        ]
    },
    {
        "version": "v1.3",
        "emoji": "📅",
        "changes": [
            "**Tradução por Resposta:** Agora basta responder a uma mensagem com `=translate <idioma>`.",
            "**Tradução Rápida:** Tradução automática de mensagens com `=translate <idioma> <texto>`.",
            "**Estatísticas Globais:** Comando `=botinfo` agora mostra o total histórico de traduções.",
            "**Persistência Infinita:** Integração total com Backend para salvar dados.",
            "**Criação do help:** Comando `=help` para mostrar o menu de comandos do bot.",
            "**Criação do Changelog:** Comando `=changelog` para mostrar o histórico de atualizações do bot."
        ]
    },
    {
        "version": "v1.2",
        "emoji": "📅",
        "changes": [
            "**Segurança:** Sistema de detecção de permissões para ADMs.",
            "**Filtros de Chat:** Bot ignora stickers e emojis customizados.",
            "**Tratamento de Erros:** Mensagens explicativas em caso de falha."
        ]
    },
    {
        "version": "v1.1",
        "emoji": "📅",
        "changes": [
            "**Segurança:** Pequenos ajustes e correção de bugs."
        ]
    },
    {
        "version": "v1.0",
        "emoji": "📅",
        "changes": [
            "**Lançamento:** Funções básicas de tradução automática e comando `=setlang`.",
            "**Multi-idioma:** Suporte para mais de 50 idiomas."
        ]
    }
]