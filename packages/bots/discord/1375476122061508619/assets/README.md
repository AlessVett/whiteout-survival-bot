# Tutorial Images

## Player ID Tutorial Image

L'immagine tutorial dovrebbe mostrare chiaramente dove trovare l'ID del giocatore nel gioco WhiteoutSurvival.

### Requisiti dell'immagine:
- Formato: PNG o JPG
- Dimensioni consigliate: 800x400px (o proporzioni simili)
- Deve mostrare chiaramente il percorso: Settings → Account → Player ID
- Evidenziare dove si trova l'ID del giocatore

### Come configurare:
1. Carica l'immagine su un servizio di hosting (es. Imgur, Discord CDN, etc.)
2. Copia l'URL diretto dell'immagine
3. Aggiungi l'URL nel file `.env`:
   ```
   PLAYER_ID_TUTORIAL_IMAGE=https://your-image-url.png
   ```

### Esempio di cosa dovrebbe mostrare l'immagine:
- Screenshot del menu delle impostazioni
- Freccia o evidenziazione che punta all'opzione Account
- Screenshot della schermata Account con l'ID del giocatore evidenziato

### Note:
- L'immagine verrà mostrata automaticamente quando gli utenti devono inserire il loro ID
- Assicurati che l'URL sia accessibile pubblicamente
- L'immagine si adatterà automaticamente alla larghezza dell'embed Discord