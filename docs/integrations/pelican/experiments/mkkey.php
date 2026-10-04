<?php
// usage: KEY_USER=.. KEY_TYPE=1|2 KEY_PERMS=json KEY_NAME=.. php artisan tinker --execute "require 'mkkey.php';"
use App\Models\{ApiKey, User};
use App\Services\Api\KeyCreationService;
$u = User::where('username', getenv('KEY_USER'))->firstOrFail();
$type = (int) getenv('KEY_TYPE');
$perms = json_decode(getenv('KEY_PERMS') ?: '{}', true);
$k = app(KeyCreationService::class)->setKeyType($type)->handle(['user_id' => $u->id, 'memo' => 'UT discovery ' . getenv('KEY_NAME'), 'allowed_ips' => [], 'permissions' => $perms]);
file_put_contents('/srv/pelican/secrets/' . getenv('KEY_NAME') . '.key', $k->identifier . $k->token);
echo getenv('KEY_NAME'), ' ', $k->identifier, PHP_EOL;
