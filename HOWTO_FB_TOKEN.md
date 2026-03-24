The Facebook access token needs to be updated every two months. This is because facebook updated their API token policies to combat politically motivated bot posting.

- go to https://developers.facebook.com/tools/explorer/

    make sure you're loggged into a facebook identity that has admin rights on the "New Project Gutenberg Books" page

- in the right panel..
 - choose facebook app "Project Gutenberg"
 - choose page or user "New Project Gutenberg Books"
 - make sure `pages_manage_posts` permissions are listed
 - DO NOT click "Get Access Token"
 - click "copy Token"
 
- Go to https://developers.facebook.com/tools/debug/accesstoken/
 - paste the token
 - click debug
 - click "extend access token"
 - click debug on the new token
 - verify that "expires" is in 2 months
 - verify that the token 'type' is 'page'
 - copy the token

- paste the token into a new file named `.fb_access_token`

- copy the access token file to the gutenbackend home directory: `scp .fb_access_token gutenbackend@gutenberg.login.ibiblio.org:~/.fb_access_token`

put a reminder on your calendar for a few days before token expiration

"New Project Gutenberg Books" is a Facebook "page."
