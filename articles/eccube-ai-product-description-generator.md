---
title: "EC-CUBE 4で商品説明文をAIで自動生成するプラグインを作る"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "php", "openai", "ai"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

ECサイト運営で地味に時間がかかるのが**商品説明文の作成**です。

- 商品数が多いと1つ1つ書くのが大変
- SEOを意識した文章を書くのが難しい
- 似たような商品だと説明文がマンネリ化する

こんな悩みを解決するため、**AIで商品説明文を自動生成するプラグイン**の仕組みを解説します。

:::message
実際に動作するプラグインは [kurozumi/eccube-plugin-chatgpt](https://github.com/kurozumi/eccube-plugin-chatgpt) で公開しています。本記事ではこのプラグインの実装を解説します。
:::

## プラグインの機能

- 商品編集画面でChatGPTに指示を送信
- 生成された説明文を商品説明欄に自動入力
- 会話履歴を保持して対話形式でやり取り可能
- ニュース編集画面にも対応
- 管理画面でAPIキーやモデル、システムプロンプトを設定可能

## ディレクトリ構成

```
app/Plugin/ChatGpt/
├── Controller/
│   └── Admin/
│       └── ChatGptController.php
├── Entity/
│   └── ChatGpt.php
├── Form/
│   └── Type/
│       └── Admin/
│           └── ChatGptType.php
├── Repository/
│   └── ChatGptRepository.php
├── Resource/
│   ├── config/
│   │   └── services.yaml
│   └── template/
│       └── admin/
│           ├── config.twig
│           └── Product/
│               └── edit.twig
├── Event.php
├── Nav.php
├── PluginManager.php
└── composer.json
```

## 実装の解説

### 1. OpenAI PHPライブラリの利用

このプラグインでは [orhanerday/open-ai](https://github.com/orhanerday/open-ai) ライブラリを使用しています。

```json
{
    "name": "ec-cube/chatgpt",
    "version": "4.3.1",
    "description": "ChatGPT for EC-CUBE",
    "type": "eccube-plugin",
    "require": {
        "ec-cube/plugin-installer": "~0.0.7 || ^2.0",
        "orhanerday/open-ai": "*"
    },
    "extra": {
        "code": "ChatGpt"
    }
}
```

### 2. 設定を保存するEntity

APIキー、モデル、システムプロンプトをデータベースに保存します。

```php
<?php

namespace Plugin\ChatGpt\Entity;

use Doctrine\ORM\Mapping as ORM;

/**
 * @ORM\Table(name="plg_chat_gpt")
 * @ORM\Entity(repositoryClass="Plugin\ChatGpt\Repository\ChatGptRepository")
 */
class ChatGpt
{
    public const ID = 1;

    /**
     * @ORM\Column(type="integer", options={"unsigned": true})
     * @ORM\Id()
     * @ORM\GeneratedValue(strategy="IDENTITY")
     */
    private $id;

    /**
     * @ORM\Column(type="string", nullable=true)
     */
    private $apiKey;

    /**
     * @ORM\Column(type="string", nullable=true)
     */
    private $model;

    /**
     * @ORM\Column(type="text", nullable=true)
     */
    private $product;  // 商品説明用のシステムプロンプト

    /**
     * @ORM\Column(type="text", nullable=true)
     */
    private $news;  // ニュース用のシステムプロンプト

    // getter/setter省略
}
```

### 3. API通信を行うController

ChatGPTへのリクエストを処理するコントローラーです。

```php
<?php

namespace Plugin\ChatGpt\Controller\Admin;

use Eccube\Controller\AbstractController;
use Orhanerday\OpenAi\OpenAi;
use Plugin\ChatGpt\Entity\ChatGpt;
use Plugin\ChatGpt\Repository\ChatGptRepository;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

/**
 * @Route("/%eccube_admin_route%/chat_gpt")
 */
class ChatGptController extends AbstractController
{
    public function __construct(
        private OpenAi $openAi,
        private ChatGptRepository $chatGptRepository,
    ) {
    }

    /**
     * @Route("/product", name="admin_chat_gpt_product", methods={"POST"})
     */
    public function product(Request $request): Response
    {
        $this->isTokenValid();

        /** @var ChatGpt $chatGpt */
        $chatGpt = $this->chatGptRepository->get(ChatGpt::ID);

        $content = json_decode($request->getContent(), true);

        $messages = [
            [
                'role' => 'user',
                'content' => $content['prompt'],
            ],
        ];

        // システムプロンプトが設定されていれば追加
        if (null !== $chatGpt->getProduct()) {
            $messages[] = [
                'role' => 'system',
                'content' => $chatGpt->getProduct(),
            ];
        }

        $chat = $this->openAi->chat([
            'model' => $chatGpt->getModel(),
            'messages' => $messages,
        ]);

        return new Response($chat);
    }
}
```

### 4. 商品編集画面へのUI追加

EventSubscriberでテンプレートを挿入します。

```php
<?php

namespace Plugin\ChatGpt;

use Eccube\Event\TemplateEvent;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

class Event implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [
            '@admin/Product/product.twig' => 'onRenderAdminProductEdit',
            '@admin/Content/news_edit.twig' => 'onRenderAdminContentNewsEdit',
        ];
    }

    public function onRenderAdminProductEdit(TemplateEvent $event): void
    {
        $event->addSnippet('@ChatGpt/admin/Product/edit.twig');
    }

    public function onRenderAdminContentNewsEdit(TemplateEvent $event): void
    {
        $event->addSnippet('@ChatGpt/admin/Content/news_edit.twig');
    }
}
```

### 5. フロントエンドの実装

JavaScriptで会話履歴を保持しながらAPIと通信します。

```twig
<div class="row" id="chat">
    <div class="col-3">
        <span>ChatGPTで商品説明を作成する</span>
    </div>
    <div class="col mb-2">
        <div id="chat-log"></div>
        <textarea id="user-input" class="form-control mb-2" rows="8"
                  placeholder="文章を入力してください"></textarea>
        <input type="button" id="send-button" class="btn btn-primary"
               value="ChatGPTにメッセージを送信する">
    </div>
</div>

<script>
$(function () {
    $('#addComment').before($('#chat'));

    // 会話履歴を保持
    let conversationHistory = [];

    async function getChatResponse(userInput) {
        const history = conversationHistory.concat(userInput).join('\n');

        const response = await fetch('{{ path('admin_chat_gpt_product') }}', {
            method: 'POST',
            headers: {
                'ECCUBE-CSRF-TOKEN': $('meta[name="eccube-csrf-token"]').attr('content'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 'prompt': history })
        });

        const data = await response.json();
        conversationHistory.push(userInput);

        return data.error
            ? data.error.message
            : data.choices[0].message.content.trim();
    }

    document.getElementById('send-button').addEventListener('click', async () => {
        const userInput = document.getElementById('user-input').value;
        const chatLog = document.getElementById('chat-log');

        // ユーザーの入力を表示
        const userMessageElement = document.createElement('div');
        userMessageElement.innerText = `あなた: ${userInput}`;
        chatLog.appendChild(userMessageElement);

        const botResponse = await getChatResponse(userInput);

        if (botResponse.error) {
            const botMessageElement = document.createElement('div');
            botMessageElement.innerText = `ChatGPT: ${botResponse}`;
            chatLog.appendChild(botMessageElement);
        } else {
            // 生成結果を商品説明欄に入力
            const textarea = document.getElementById('admin_product_description_detail');
            textarea.value = botResponse;
        }

        document.getElementById('user-input').value = '';
    });
});
</script>
```

### 6. OpenAiサービスの登録

`services.yaml`でOpenAiクラスをDIコンテナに登録します。

```yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true

    Plugin\ChatGpt\:
        resource: '../../*'
        exclude: '../../{Entity}'

    Orhanerday\OpenAi\OpenAi:
        arguments:
            $OPENAI_API_KEY: '%env(OPENAI_API_KEY)%'
```

## 効果的なプロンプト設計

管理画面で設定できるシステムプロンプトの例です。

### 商品説明用プロンプト

```
あなたはECサイトの商品説明文を作成するプロのコピーライターです。

以下のルールに従って商品説明文を作成してください：
- 200〜400文字程度で作成
- 最初の一文で商品の魅力を端的に伝える
- 箇条書きは使わず、自然な文章で
- 誇大表現は避け、事実に基づいた内容で
- HTMLタグは使用しない
- 購買意欲を高める表現を使う
```

### SEO最適化プロンプト

```
あなたはSEOに精通したECサイトのコピーライターです。

以下のルールに従って商品説明文を作成してください：
- ターゲットキーワードを自然に2〜3回含める
- 最初の100文字に重要なキーワードを配置
- ユーザーの検索意図に応える内容
- 具体的な数値や事実を含める
- 行動を促すフレーズで締める
```

## カスタマイズ例

### Claude API対応版

OpenAIではなくAnthropic Claude APIを使用する場合の実装例です。

```php
<?php

namespace Plugin\ChatGpt\Service;

class ClaudeService
{
    private string $apiKey;
    private string $endpoint = 'https://api.anthropic.com/v1/messages';

    public function __construct()
    {
        $this->apiKey = $_ENV['ANTHROPIC_API_KEY'] ?? '';
    }

    public function chat(string $prompt, ?string $systemPrompt = null): string
    {
        $messages = [
            ['role' => 'user', 'content' => $prompt],
        ];

        $data = [
            'model' => 'claude-sonnet-4-20250514',
            'max_tokens' => 1024,
            'messages' => $messages,
        ];

        if ($systemPrompt) {
            $data['system'] = $systemPrompt;
        }

        $ch = curl_init($this->endpoint);

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'x-api-key: ' . $this->apiKey,
                'anthropic-version: 2023-06-01',
            ],
            CURLOPT_POSTFIELDS => json_encode($data),
        ]);

        $response = curl_exec($ch);
        curl_close($ch);

        $result = json_decode($response, true);

        return $result['content'][0]['text'] ?? '';
    }
}
```

### チャット形式UIへの改善

より使いやすいチャット形式のインターフェースに改善するサンプルコードです。

```twig
{# app/Plugin/ChatGpt/Resource/template/admin/Product/edit.twig #}

<style>
.chat-container {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    background: #f8f9fa;
    margin-bottom: 1rem;
}

.chat-header {
    background: #495057;
    color: white;
    padding: 12px 16px;
    border-radius: 8px 8px 0 0;
    font-weight: bold;
}

.chat-messages {
    height: 300px;
    overflow-y: auto;
    padding: 16px;
    background: white;
}

.chat-message {
    margin-bottom: 12px;
    display: flex;
    flex-direction: column;
}

.chat-message.user {
    align-items: flex-end;
}

.chat-message.assistant {
    align-items: flex-start;
}

.chat-bubble {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 16px;
    line-height: 1.5;
    white-space: pre-wrap;
}

.chat-message.user .chat-bubble {
    background: #0d6efd;
    color: white;
    border-bottom-right-radius: 4px;
}

.chat-message.assistant .chat-bubble {
    background: #e9ecef;
    color: #212529;
    border-bottom-left-radius: 4px;
}

.chat-label {
    font-size: 11px;
    color: #6c757d;
    margin-bottom: 4px;
}

.chat-input-area {
    padding: 12px;
    border-top: 1px solid #dee2e6;
    background: #f8f9fa;
    border-radius: 0 0 8px 8px;
}

.chat-typing {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 10px 14px;
    background: #e9ecef;
    border-radius: 16px;
    width: fit-content;
}

.chat-typing span {
    width: 8px;
    height: 8px;
    background: #6c757d;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;
}

.chat-typing span:nth-child(2) { animation-delay: 0.2s; }
.chat-typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 100% { opacity: 0.3; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1); }
}

.chat-actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
}
</style>

<div class="row mb-3" id="chat-gpt-section">
    <div class="col-3">
        <span>ChatGPTで商品説明を作成</span>
    </div>
    <div class="col">
        <div class="chat-container">
            <div class="chat-header">
                <i class="fa fa-robot me-2"></i>AI アシスタント
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="chat-message assistant">
                    <span class="chat-label">AI アシスタント</span>
                    <div class="chat-bubble">
                        こんにちは！商品説明文の作成をお手伝いします。<br>
                        商品名や特徴を教えてください。
                    </div>
                </div>
            </div>
            <div class="chat-input-area">
                <textarea id="chat-input" class="form-control mb-2" rows="3"
                          placeholder="例: この商品の説明文を200文字程度で作成してください"></textarea>
                <div class="d-flex justify-content-between align-items-center">
                    <div class="chat-actions">
                        <button type="button" class="btn btn-outline-secondary btn-sm" id="btn-clear-chat">
                            <i class="fa fa-trash me-1"></i>履歴クリア
                        </button>
                        <button type="button" class="btn btn-outline-success btn-sm" id="btn-apply-text">
                            <i class="fa fa-check me-1"></i>説明文に反映
                        </button>
                    </div>
                    <button type="button" class="btn btn-primary" id="btn-send-chat">
                        <i class="fa fa-paper-plane me-1"></i>送信
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
$(function () {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send-chat');
    const btnClear = document.getElementById('btn-clear-chat');
    const btnApply = document.getElementById('btn-apply-text');
    const descriptionField = document.getElementById('admin_product_description_detail');

    let conversationHistory = [];
    let lastAssistantMessage = '';

    // メッセージを追加
    function addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;

        const label = document.createElement('span');
        label.className = 'chat-label';
        label.textContent = role === 'user' ? 'あなた' : 'AI アシスタント';

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        bubble.textContent = content;

        messageDiv.appendChild(label);
        messageDiv.appendChild(bubble);
        chatMessages.appendChild(messageDiv);

        // スクロールを下に
        chatMessages.scrollTop = chatMessages.scrollHeight;

        if (role === 'assistant') {
            lastAssistantMessage = content;
        }
    }

    // ローディング表示
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant';
        typingDiv.id = 'typing-indicator';

        const typing = document.createElement('div');
        typing.className = 'chat-typing';
        typing.innerHTML = '<span></span><span></span><span></span>';

        typingDiv.appendChild(typing);
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function hideTyping() {
        const typing = document.getElementById('typing-indicator');
        if (typing) typing.remove();
    }

    // メッセージ送信
    async function sendMessage() {
        const userInput = chatInput.value.trim();
        if (!userInput) return;

        // 商品名を自動で含める
        const productName = document.querySelector('input[name="admin_product[name]"]')?.value;
        let prompt = userInput;
        if (productName && conversationHistory.length === 0) {
            prompt = `商品名: ${productName}\n\n${userInput}`;
        }

        addMessage(userInput, 'user');
        chatInput.value = '';
        btnSend.disabled = true;

        showTyping();

        try {
            const history = conversationHistory.concat(prompt).join('\n');

            const response = await fetch('{{ path('admin_chat_gpt_product') }}', {
                method: 'POST',
                headers: {
                    'ECCUBE-CSRF-TOKEN': $('meta[name="eccube-csrf-token"]').attr('content'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt: history })
            });

            const data = await response.json();
            hideTyping();

            if (data.error) {
                addMessage('エラー: ' + data.error.message, 'assistant');
            } else {
                const assistantMessage = data.choices[0].message.content.trim();
                addMessage(assistantMessage, 'assistant');
                conversationHistory.push(prompt);
                conversationHistory.push(assistantMessage);
            }
        } catch (error) {
            hideTyping();
            addMessage('通信エラーが発生しました。', 'assistant');
        }

        btnSend.disabled = false;
    }

    // イベントリスナー
    btnSend.addEventListener('click', sendMessage);

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            sendMessage();
        }
    });

    btnClear.addEventListener('click', () => {
        conversationHistory = [];
        lastAssistantMessage = '';
        chatMessages.innerHTML = `
            <div class="chat-message assistant">
                <span class="chat-label">AI アシスタント</span>
                <div class="chat-bubble">
                    こんにちは！商品説明文の作成をお手伝いします。<br>
                    商品名や特徴を教えてください。
                </div>
            </div>
        `;
    });

    btnApply.addEventListener('click', () => {
        if (!lastAssistantMessage) {
            alert('反映するメッセージがありません');
            return;
        }
        if (descriptionField.value && !confirm('既存の説明文を上書きしますか？')) {
            return;
        }
        descriptionField.value = lastAssistantMessage;
    });
});
</script>
```

**改善ポイント**:
- 吹き出し形式でユーザー/AIのメッセージを区別
- タイピングアニメーションでローディング表示
- 「説明文に反映」ボタンで最後のAI回答を適用
- 「履歴クリア」ボタンで会話をリセット
- Ctrl+Enterでメッセージ送信
- 商品名を自動で最初のプロンプトに含める

## 注意点

### 1. APIキーの管理

APIキーは管理画面から設定し、`.env`ファイルに保存されます。**Gitにコミットしない**ように注意してください。

### 2. API利用料金

生成のたびにAPI料金が発生します。

| 生成数 | 概算料金（GPT-4o） |
|--------|-------------------|
| 100商品 | 約$0.50〜$1.00 |
| 1,000商品 | 約$5.00〜$10.00 |

### 3. 生成内容の確認

AIが生成した内容は必ず人間がチェックしてください。

- 事実と異なる内容が含まれていないか
- 誇大広告にあたる表現はないか
- 他社商品の説明文と酷似していないか

### 4. レートリミット

OpenAI APIにはレートリミットがあります。一括生成する場合は適切な間隔を空けて実行してください。

## まとめ

- EC-CUBE 4でAIを活用した商品説明文の自動生成が簡単に実装できる
- `orhanerday/open-ai`ライブラリで手軽にAPI連携
- 会話履歴を保持することで対話形式での調整が可能
- システムプロンプトのカスタマイズでSEO最適化も可能

プラグインは [GitHub](https://github.com/kurozumi/eccube-plugin-chatgpt) で公開しています。ぜひお試しください。

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
