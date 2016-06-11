
AddHandler fcgid-script .fcgi
Options +FollowSymLinks
RewriteEngine On
RewriteBase /scoretility/

# no caching
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType text/html "now"
    ExpiresDefault "now"
</IfModule>

# everything else sent to flask
RewriteRule ^(rrwebappdispatch\.fcgi/.*)$ - [L]
RewriteRule ^(.*)$ rrwebappdispatch.fcgi/$1 [L]


