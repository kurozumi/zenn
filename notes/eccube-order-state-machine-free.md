# EC-CUBE 4のOrderStateMachineを理解する - Symfony Workflowで実現する受注ステータス管理

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

EC-CUBE 4では、受注ステータスの遷移管理にSymfony Workflow Componentを採用しています。この記事では、OrderStateMachineの仕組みを詳しく解説し、プラグインでの活用方法を紹介します。