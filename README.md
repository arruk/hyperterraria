# HyperTerraria

Mod client-side para tModLoader 1.4.x que substitui nomes de itens vanilla por
versões hypertraduzidas em português.

Hypertranslation faz um texto passar por vários idiomas antes de retornar ao
português. O HyperTerraria **não traduz nada durante o jogo**: ele lê traduções
prontas de `Assets/hyper_items_ptBR.json`. Não há chamadas de API, dependências
externas ou chaves secretas.

## Requisitos

- Terraria e tModLoader 1.4.x instalados.
- Windows com PowerShell para usar os scripts opcionais.
- Git, caso o projeto seja clonado.

## Instalação

1. Clone o repositório:

   ```powershell
   git clone <URL-DO-REPOSITORIO> HyperTerraria
   cd HyperTerraria
   ```

2. A pasta padrão de fontes de mods no Windows é:

   ```text
   %USERPROFILE%\Documents\My Games\Terraria\tModLoader\ModSources
   ```

   Em instalações nas quais a pasta Documentos foi movida pelo Windows ou
   OneDrive, localize a pasta equivalente usada pelo tModLoader.

3. Escolha uma destas formas de instalar:

   - Copie a pasta inteira do repositório para `ModSources\HyperTerraria`.
   - Para copiar e atualizar o destino automaticamente:

     ```powershell
     powershell -ExecutionPolicy Bypass -File .\scripts\copy-to-modsources.ps1
     ```

   - Para criar um link simbólico e editar o clone diretamente:

     ```powershell
     powershell -ExecutionPolicy Bypass -File .\scripts\install-to-modsources.ps1
     ```

     A criação do link exige o Modo de Desenvolvedor do Windows ou um
     PowerShell executado como administrador. O destino não pode existir.

## Compilar, testar e ativar

1. Abra o tModLoader.
2. Acesse **Workshop > Develop Mods**.
3. Encontre `HyperTerraria` e escolha **Build + Reload**.
4. Volte ao menu de Workshop, abra **Manage Mods**, ative `HyperTerraria` e
   selecione **Reload Mods** quando solicitado.
5. Entre em um mundo e confira os nomes dos itens presentes no cache.
6. Em **Settings > Mod Configuration > HyperTerraria**, use:
   - `EnableItemNames`: liga ou desliga a substituição de nomes.
   - `LogChangedItems`: registra cada substituição no log do tModLoader.

Se o JSON estiver ausente, vazio ou inválido, o mod registra o problema e
continua carregando sem substituir nomes.

## Editar as hypertraduções

Edite `Assets/hyper_items_ptBR.json` mantendo um objeto JSON no formato:

```json
{
  "ItemName.CopperShortsword": "Espada curta de cobre que viajou demais",
  "ItemName.IronPickaxe": "Picareta de ferro internacionalmente confusa"
}
```

As chaves precisam corresponder às chaves vanilla e começar com `ItemName.`.
Valores vazios e outros prefixos são ignorados. Salve o arquivo em UTF-8 e use
**Build + Reload** novamente. JSON não aceita duas entradas com a mesma chave;
também é recomendável não deixar vírgula depois da última entrada.

## Como funciona

Durante `OnModLoad`, o sistema desserializa o cache empacotado. Depois que as
localizações do jogo são carregadas, `OnLocalizationsLoaded` procura chaves
`ItemName.*`, encontra as que também estão no cache e chama por reflection o
método não público `LocalizedText.SetValue`. Essa reflection é necessária
porque textos vanilla não expõem um setter público.

O mod só muda localização no cliente. Não altera itens, receitas, atributos,
gameplay ou arquivos da instalação do Terraria.

## Expansão futura

Para adicionar NPCs e bosses, crie caches e sistemas equivalentes para o
prefixo `NPCName.`. O mesmo padrão pode ser usado para `ItemTooltip.`,
`BuffName.` e outros grupos:

1. carregue apenas entradas do prefixo permitido;
2. encontre apenas localizações já registradas pelo Terraria;
3. respeite uma opção client-side própria;
4. aplique os valores somente em `OnLocalizationsLoaded`;
5. mantenha falhas de cache e reflection não fatais.

Essa separação evita misturar grupos e mantém claro quais textos cada versão
do mod pode modificar.

## Gerar um cache completo

Para incluir todos os itens, primeiro obtenha um ou mais arquivos JSON de
localização inglesa que contenham as chaves vanilla e seus textos. O script
`scripts/generate-item-cache.py` lê exclusivamente o objeto `ItemName` na
primeira camada:

```json
{
  "ItemName": {
    "CopperShortsword": "Copper Shortsword"
  }
}
```

Execute com Python 3:

```powershell
python .\scripts\generate-item-cache.py .\caminho\en-US.json
```

Também é possível combinar vários arquivos:

```powershell
python .\scripts\generate-item-cache.py .\localization\Items.json .\localization\Legacy.json
```

Por segurança, o script preserva valores já existentes em
`Assets/hyper_items_ptBR.json`. Chaves novas recebem temporariamente o texto
inglês. Ele não chama APIs e não produz hypertraduções sozinho; a etapa de
tradução deve atualizar esses valores antes de publicar o cache. Para recriar
todos os valores a partir do inglês, use `--overwrite-existing`.

Categorias irmãs como `ItemTooltip`, `NPCName` e `BuffName` são ignoradas.
Referências puras como `{$PaintingArtist.Myhre}` são sempre mantidas em inglês.
Em textos mistos, traduções existentes só são preservadas quando mantêm
exatamente referências e placeholders como `{$Category.Key}`, `{0}` e
`{^0:item;items}`; valores que corrompam esses tokens são substituídos pelo
original inglês e produzem um aviso.

## Gerar as hypertraduções localmente

O script `scripts/hypertranslate-items.py` usa por padrão o modelo local
`facebook/nllb-200-distilled-600M`. Ele não exige API key e, depois do primeiro
download, pode funcionar offline. O modelo possui licença CC-BY-NC-4.0 e é
destinado a pesquisa, não a produção comercial.

### Preparação

Use Python 3 de 64 bits. Na raiz do repositório, instale as dependências:

```powershell
python -m pip install torch transformers sentencepiece
```

O arquivo de entrada deve ser o recurso inglês extraído do Terraria e precisa
conter `ItemName` na primeira camada. O caminho usado nos exemplos é:

```text
Localization/Terraria.Localization.Content.en-US.Items.json
```

### Conferir sem traduzir

O modo `--dry-run` mostra a cadeia e a quantidade de itens sem baixar o modelo,
alterar o cache ou executar traduções:

```powershell
python .\scripts\hypertranslate-items.py `
  .\Localization\Terraria.Localization.Content.en-US.Items.json `
  --provider nllb `
  --dry-run
```

Por padrão, a cadeia contém 10 idiomas no total: nove intermediários escolhidos
sem repetição entre 50 opções e `pt-BR` como destino final. A seleção é
reproduzível pela semente.

### Fazer um teste pequeno

Antes da execução completa, traduza dois itens usando cinco idiomas:

```powershell
python .\scripts\hypertranslate-items.py `
  .\Localization\Terraria.Localization.Content.en-US.Items.json `
  --provider nllb `
  --language-count 5 `
  --limit 2
```

Na primeira execução efetiva, os arquivos do modelo serão baixados
automaticamente pelo Hugging Face.

### Traduzir todos os itens

Para processar todos os itens com os 10 idiomas padrão:

```powershell
python .\scripts\hypertranslate-items.py `
  .\Localization\Terraria.Localization.Content.en-US.Items.json `
  --provider nllb
```

Como `nllb` é o provedor padrão, a forma curta equivalente é:

```powershell
python .\scripts\hypertranslate-items.py `
  .\Localization\Terraria.Localization.Content.en-US.Items.json
```

No Git Bash, use barras normais e `\` para continuar uma linha:

```bash
python scripts/hypertranslate-items.py \
  Localization/Terraria.Localization.Content.en-US.Items.json \
  --provider nllb
```

O resultado é gravado por padrão em:

```text
Assets/hyper_items_ptBR.json
```

Depois da tradução, execute **Workshop > Develop Mods > Build + Reload** no
tModLoader para empacotar o cache atualizado.

### Opções úteis

- `--language-count N`: total de idiomas da cadeia, incluindo `pt-BR`; aceita
  valores de 2 a 51 e usa 10 por padrão.
- `--seed TEXTO`: altera de maneira reproduzível quais idiomas serão escolhidos
  e em qual ordem.
- `--limit N`: processa somente os primeiros `N` candidatos.
- `--retranslate`: refaz inclusive valores que já diferem do inglês.
- `--output CAMINHO`: escolhe outro arquivo JSON de saída.
- `--model MODELO`: escolhe outro checkpoint NLLB compatível.
- `--dry-run`: apenas exibe o plano, sem carregar o modelo ou escrever arquivos.
- `--help`: mostra todas as opções disponíveis.

O cache é salvo atomicamente após cada item. Uma execução interrompida pode ser
retomada com o mesmo comando: valores que já diferem do inglês são preservados.
Use `--retranslate` somente quando quiser refazer traduções existentes.
Referências puras são ignoradas, e placeholders são protegidos e validados
entre todas as etapas. A opção `--seed` produz outra sequência de idiomas.

Na primeira execução, o Hugging Face baixa aproximadamente alguns gigabytes de
arquivos do modelo. O script usa CUDA automaticamente quando PyTorch detecta
uma GPU NVIDIA compatível; caso contrário, usa CPU e pode demorar bastante.
O download exige internet, mas as execuções seguintes usam o modelo armazenado
no cache local.

O provedor anterior continua disponível opcionalmente com
`--provider google --yes`. Ele requer `GOOGLE_TRANSLATE_API_KEY` e pode gerar
cobrança; não é necessário para o modo NLLB.
